import logging, threading, queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from app.scanner import scan_folders
from app.database import DocuMindDatabase
from app.processing_service import ProcessingService
from app.rules_engine import RulesEngine
from app.rules_editor import RulesEditor

logger=logging.getLogger(__name__)

class DocuMindWindow:
    def __init__(self, config_manager):
        self.config=config_manager
        self.root=tk.Tk()
        self.root.title("DocuMind — реестр документов (тестовая сборка 0.1)")
        self.root.geometry("1100x700"); self.root.minsize(800,500)
        self.folders=[]; self.queue=queue.Queue(); self.cancel_event=threading.Event(); self.worker=None
        self.output_var=tk.StringVar()
        self.status_var=tk.StringVar(value="Готово к работе.")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW",self._close)
        self.root.after(100,self._poll)

    def _build(self):
        self.root.columnconfigure(0,weight=1); self.root.rowconfigure(2,weight=1)
        top=ttk.Frame(self.root,padding=10); top.grid(row=0,column=0,sticky="ew")
        ttk.Label(top,text="Папки с документами").grid(row=0,column=0,sticky="w")
        ttk.Button(top,text="Добавить папку",command=self._add_folder).grid(row=0,column=1,padx=4)
        ttk.Button(top,text="Удалить выбранную",command=self._remove_folder).grid(row=0,column=2,padx=4)
        ttk.Button(top,text="Очистить список",command=self._clear_folders).grid(row=0,column=3,padx=4)
        self.folder_list=tk.Listbox(top,height=4); self.folder_list.grid(row=1,column=0,columnspan=4,sticky="ew",pady=6)
        top.columnconfigure(0,weight=1)
        export=ttk.Frame(self.root,padding=(10,0,10,8)); export.grid(row=1,column=0,sticky="ew"); export.columnconfigure(1,weight=1)
        ttk.Label(export,text="Excel-реестр").grid(row=0,column=0,sticky="w")
        ttk.Entry(export,textvariable=self.output_var).grid(row=0,column=1,sticky="ew",padx=5)
        ttk.Button(export,text="Выбрать…",command=self._choose_output).grid(row=0,column=2,padx=3)
        ttk.Button(export,text="Правила анализа",command=self._open_rules).grid(row=0,column=3,padx=3)
        ttk.Button(export,text="Начать обработку",command=self._start).grid(row=0,column=4,padx=3)
        area=ttk.Frame(self.root,padding=(10,0,10,8)); area.grid(row=2,column=0,sticky="nsew"); area.rowconfigure(0,weight=1); area.columnconfigure(0,weight=1)
        cols=("name","type","status","fields","summary")
        self.tree=ttk.Treeview(area,columns=cols,show="headings")
        for col,title,width in [("name","Файл",220),("type","Формат",70),("status","Статус",85),("fields","Найдено полей",150),("summary","Выжимка",450)]:
            self.tree.heading(col,text=title); self.tree.column(col,width=width,anchor="w")
        y=ttk.Scrollbar(area,orient="vertical",command=self.tree.yview); x=ttk.Scrollbar(area,orient="horizontal",command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        self.tree.grid(row=0,column=0,sticky="nsew"); y.grid(row=0,column=1,sticky="ns"); x.grid(row=1,column=0,sticky="ew")
        bottom=ttk.Frame(self.root,padding=10); bottom.grid(row=3,column=0,sticky="ew"); bottom.columnconfigure(0,weight=1)
        self.progress=ttk.Progressbar(bottom,mode="determinate"); self.progress.grid(row=0,column=0,sticky="ew",padx=(0,8))
        ttk.Button(bottom,text="Отменить",command=self._cancel).grid(row=0,column=1)
        ttk.Label(bottom,textvariable=self.status_var).grid(row=1,column=0,columnspan=2,sticky="w",pady=(5,0))

    def _add_folder(self):
        path=filedialog.askdirectory(parent=self.root)
        if path and path not in self.folders:
            self.folders.append(path); self.folder_list.insert(tk.END,path)

    def _remove_folder(self):
        sel=self.folder_list.curselection()
        if sel:
            idx=sel[0]; self.folder_list.delete(idx); del self.folders[idx]

    def _clear_folders(self):
        self.folders.clear(); self.folder_list.delete(0,tk.END)

    def _choose_output(self):
        path=filedialog.asksaveasfilename(parent=self.root,title="Выбрать Excel-реестр",defaultextension=".xlsx",filetypes=[("Excel","*.xlsx")])
        if path:self.output_var.set(path)

    def _open_rules(self):
        try:
            engine=RulesEngine(self.config.rules_path)
            RulesEditor(self.root,engine)
        except Exception as e:
            messagebox.showerror("Правила анализа",str(e),parent=self.root)

    def _start(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("DocuMind","Обработка уже выполняется.",parent=self.root); return
        if not self.folders:
            messagebox.showwarning("DocuMind","Добавьте хотя бы одну папку.",parent=self.root); return
        output=self.output_var.get().strip()
        if not output or Path(output).suffix.lower()!=".xlsx":
            messagebox.showwarning("DocuMind","Выберите путь к файлу .xlsx.",parent=self.root); return
        files=list(scan_folders(self.folders,recursive=True,skip_hidden=True))
        if not files:
            messagebox.showinfo("DocuMind","Поддерживаемые документы PDF, DOCX и XLSX не найдены.",parent=self.root); return
        self.cancel_event.clear(); self.progress.configure(maximum=len(files),value=0)
        self.status_var.set(f"Найдено документов: {len(files)}. Обработка…")
        for iid in self.tree.get_children():self.tree.delete(iid)
        self.worker=threading.Thread(target=self._worker_main,args=(files,output),daemon=False)
        self.worker.start()

    def _worker_main(self,files,output):
        try:
            db=DocuMindDatabase(self.config.database_path)
            from app.analyzer import DocumentAnalyzer
            analyzer=DocumentAnalyzer(self.config.rules_path)
            service=ProcessingService(db,analyzer=analyzer)
            def progress(done,total,path): self.queue.put(("progress",done,total,path))
            result=service.process_files(files,output,progress_callback=progress,cancel_event=self.cancel_event)
            self.queue.put(("finished",result))
        except Exception as e:
            logger.exception("Сбой рабочего потока")
            self.queue.put(("fatal",f"{type(e).__name__}: {e}"))

    def _cancel(self):
        self.cancel_event.set(); self.status_var.set("Запрошена отмена; завершается текущий документ…")

    def _poll(self):
        try:
            while True:
                item=self.queue.get_nowait(); kind=item[0]
                if kind=="progress":
                    _,done,total,path=item; self.progress.configure(value=done)
                    self.status_var.set(f"{done}/{total}: {Path(path).name}")
                elif kind=="finished":
                    result=item[1]
                    for i,record in enumerate(result["records"]):
                        found=len(record.get("fields",{}))
                        self.tree.insert("",tk.END,iid=f"r{i}",values=(record["file_name"],record["file_type"],record["status"],found,record.get("summary","")))
                    message=f"Обработано: {result['processed']}; успешно: {result['successful']}; ошибок: {result['failed']}; кэш: {result['skipped']}; новых строк: {result['excel_rows_added']}."
                    if result["export_error"]:message += "\nОшибка Excel: "+result["export_error"]
                    if result["cancelled"]:message += "\nОбработка отменена."
                    self.status_var.set(message)
                    if result["errors"] or result["export_error"]:
                        messagebox.showwarning("Результат обработки",message,parent=self.root)
                elif kind=="fatal":
                    self.status_var.set("Ошибка запуска обработки.")
                    messagebox.showerror("DocuMind",item[1],parent=self.root)
        except queue.Empty: pass
        if self.root.winfo_exists():self.root.after(100,self._poll)

    def _close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("Выход","Обработка ещё идёт. Запросить отмену и дождаться завершения?",parent=self.root):return
            self.cancel_event.set()
            self.status_var.set("Ожидание завершения обработки…")
            self.root.after(200,self._wait_worker)
        else:self.root.destroy()

    def _wait_worker(self):
        if self.worker and self.worker.is_alive():
            self.root.after(200,self._wait_worker)
        else:self.root.destroy()

    def run(self):
        from app.logging_setup import configure_logging
        configure_logging(self.config.log_path)
        self.root.mainloop()
