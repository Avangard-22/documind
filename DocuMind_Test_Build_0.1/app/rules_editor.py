import json
import tkinter as tk
from tkinter import ttk, messagebox
from app.rules_engine import RulesEngine

class RulesEditor(tk.Toplevel):
    def __init__(self, master, engine):
        super().__init__(master)
        self.engine = engine
        self.rules = engine.get_rules()
        self.selected = None
        self.title("DocuMind — правила анализа")
        self.geometry("980x650")
        self.minsize(750, 500)
        self._build()
        self._refresh()
        self.transient(master)

    def _build(self):
        self.columnconfigure(0, weight=1); self.rowconfigure(1, weight=1)
        ttk.Label(self, text="Правила анализа документов", font=("Segoe UI", 15, "bold")).grid(row=0,column=0,sticky="w",padx=12,pady=10)
        pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL); pane.grid(row=1,column=0,sticky="nsew",padx=10,pady=5)
        left=ttk.Frame(pane,padding=5); right=ttk.Frame(pane,padding=5); pane.add(left,weight=1); pane.add(right,weight=3)
        left.rowconfigure(0,weight=1); left.columnconfigure(0,weight=1)
        self.listbox=tk.Listbox(left,exportselection=False); self.listbox.grid(row=0,column=0,sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>",self._select)
        ttk.Button(left,text="Добавить",command=self._add).grid(row=1,column=0,sticky="ew",pady=3)
        ttk.Button(left,text="Удалить",command=self._delete).grid(row=2,column=0,sticky="ew",pady=3)
        right.columnconfigure(1,weight=1); right.rowconfigure(4,weight=1)
        self.name=tk.StringVar(); self.label=tk.StringVar(); self.enabled=tk.BooleanVar(value=True)
        ttk.Label(right,text="Имя поля").grid(row=0,column=0,sticky="w",pady=3)
        ttk.Entry(right,textvariable=self.name).grid(row=0,column=1,sticky="ew",pady=3)
        ttk.Label(right,text="Название").grid(row=1,column=0,sticky="w",pady=3)
        ttk.Entry(right,textvariable=self.label).grid(row=1,column=1,sticky="ew",pady=3)
        ttk.Checkbutton(right,text="Правило включено",variable=self.enabled).grid(row=2,column=1,sticky="w",pady=3)
        ttk.Label(right,text="Регулярные выражения — по одному на строку").grid(row=3,column=0,columnspan=2,sticky="w")
        self.patterns=tk.Text(right,wrap="none",font=("Consolas",10)); self.patterns.grid(row=4,column=0,columnspan=2,sticky="nsew",pady=4)
        ttk.Label(right,text="Текст для тестирования").grid(row=5,column=0,columnspan=2,sticky="w")
        self.sample=tk.Text(right,height=5,wrap="word"); self.sample.grid(row=6,column=0,columnspan=2,sticky="ew",pady=4)
        self.result=tk.Text(right,height=5,wrap="word",state="disabled"); self.result.grid(row=7,column=0,columnspan=2,sticky="ew")
        foot=ttk.Frame(self,padding=10); foot.grid(row=2,column=0,sticky="ew")
        ttk.Button(foot,text="Применить к полю",command=self._apply).pack(side="left",padx=3)
        ttk.Button(foot,text="Проверить шаблоны",command=self._test).pack(side="left",padx=3)
        ttk.Button(foot,text="Сохранить правила",command=self._save).pack(side="right")

    def _refresh(self):
        self.listbox.delete(0,tk.END)
        for f in self.rules["fields"]:
            self.listbox.insert(tk.END,("✓ " if f["enabled"] else "○ ")+f["label"])

    def _select(self,_=None):
        sel=self.listbox.curselection()
        if not sel:return
        idx=sel[0]
        if self.selected is not None and self.selected != idx and not self._apply(False):
            self.listbox.selection_clear(0,tk.END); self.listbox.selection_set(self.selected); return
        self.selected=idx; f=self.rules["fields"][idx]
        self.name.set(f["name"]); self.label.set(f["label"]); self.enabled.set(f["enabled"])
        self.patterns.delete("1.0",tk.END); self.patterns.insert("1.0","\n".join(f["patterns"]))

    def _apply(self,show=True):
        if self.selected is None:return True
        candidate=self.engine.get_rules()
        candidate["fields"]=[dict(x) for x in self.rules["fields"]]
        candidate["fields"][self.selected]={
            "name":self.name.get().strip(),"label":self.label.get().strip(),"enabled":self.enabled.get(),
            "patterns":[x.strip() for x in self.patterns.get("1.0",tk.END).splitlines() if x.strip()]
        }
        try:self.engine.validate(candidate)
        except ValueError as e:
            if show:messagebox.showerror("Правило",str(e),parent=self)
            return False
        self.rules=candidate; self._refresh()
        self.listbox.selection_set(self.selected)
        return True

    def _add(self):
        if not self._apply(False):return
        names={x["name"] for x in self.rules["fields"]}; n=1; name="custom_field"
        while name in names:n+=1; name=f"custom_field_{n}"
        self.rules["fields"].append({"name":name,"label":"Новое поле","enabled":True,"patterns":[]})
        self.selected=len(self.rules["fields"])-1; self._refresh(); self.listbox.selection_set(self.selected)
        self.name.set(name); self.label.set("Новое поле"); self.enabled.set(True); self.patterns.delete("1.0",tk.END)

    def _delete(self):
        sel=self.listbox.curselection()
        if not sel:return
        idx=sel[0]
        if not messagebox.askyesno("Удаление","Удалить выбранное правило?",parent=self):return
        del self.rules["fields"][idx]; self.selected=None; self._refresh()
        self.name.set(""); self.label.set(""); self.patterns.delete("1.0",tk.END)

    def _test(self):
        if not self._apply():return
        if self.selected is None:return
        sample=self.sample.get("1.0",tk.END)
        output=[]
        for p in self.rules["fields"][self.selected]["patterns"]:
            output.append({"pattern":p,**self.engine.test_pattern(p,sample)})
        self.result.configure(state="normal"); self.result.delete("1.0",tk.END)
        self.result.insert("1.0",json.dumps(output,ensure_ascii=False,indent=2)); self.result.configure(state="disabled")

    def _save(self):
        if not self._apply():return
        try:self.engine.save_rules(self.rules)
        except Exception as e:messagebox.showerror("Ошибка сохранения",str(e),parent=self); return
        messagebox.showinfo("DocuMind","Правила сохранены.",parent=self); self.destroy()
