"""Tree editor for bounded nested ALL/ANY scenario conditions."""
import copy
import tkinter as tk
from tkinter import ttk, messagebox
from lib.event_rules import normalize_expression
from lib.scenario_rules import objectives


class ExpressionDialog(tk.Toplevel):
    def __init__(self, parent, roster, expression, apply):
        super().__init__(parent)
        self.title('Nested Event Conditions')
        self.transient(parent)
        self.parent, self.roster, self.callback = parent, roster, apply
        self.objectives = objectives(roster)
        self.expression = copy.deepcopy(expression or dict(operator='all',children=[self.default_leaf()]))
        if 'children' not in self.expression:
            self.expression = dict(operator='all',children=[self.expression])
        self.selected = None
        body=ttk.Frame(self,padding=14);body.pack(fill='both',expand=True)
        ttk.Label(body,text='ALL requires every child; ANY requires at least one. Groups can contain other groups.').pack(anchor='w',pady=(0,8))
        self.tree=ttk.Treeview(body,show='tree',height=13,selectmode='browse')
        self.tree.pack(fill='both',expand=True)
        self.tree.column('#0',width=610)
        self.tree.bind('<<TreeviewSelect>>',self.select)
        bar=ttk.Frame(body);bar.pack(fill='x',pady=8)
        for text,cmd in (('Add Check',self.add_leaf),('Add ALL Group',lambda:self.add_group('all')),
                         ('Add ANY Group',lambda:self.add_group('any')),('Remove',self.remove)):
            ttk.Button(bar,text=text,command=cmd).pack(side='left',padx=3)
        form=ttk.Frame(body);form.pack(fill='x')
        self.fields={k:tk.StringVar() for k in ('kind','side','objective','threshold')}
        self.widgets={}
        for row,(key,label,options) in enumerate((('kind','Condition / group',()),('side','Side',('Allied','Axis')),
                ('objective','Objective',tuple(f'{i+1}: {o["name"]}' for i,o in enumerate(self.objectives))),
                ('threshold','Casualty points lost',None))):
            ttk.Label(form,text=label).grid(row=row,column=0,sticky='w',padx=5,pady=4)
            w=(ttk.Entry(form,textvariable=self.fields[key],width=42) if options is None else
               ttk.Combobox(form,textvariable=self.fields[key],values=options,state='readonly',width=40))
            w.grid(row=row,column=1,sticky='ew');self.widgets[key]=w
        self.widgets['kind'].bind('<<ComboboxSelected>>',lambda e:self.enable())
        ttk.Label(body,text='Up to 16 checks, 32 total nodes and four nested groups. Changes apply with the parent phase.',
                  wraplength=610).pack(anchor='w',pady=10)
        bar=ttk.Frame(body);bar.pack(fill='x')
        ttk.Button(bar,text='Use These Conditions',command=self.submit).pack(side='right')
        ttk.Button(bar,text='Cancel',command=self.close).pack(side='right',padx=6)
        self.bind('<Escape>',lambda e:self.close());self.protocol('WM_DELETE_WINDOW',self.close)
        self.refresh('0');self.grab_set()

    def default_leaf(self):
        return dict(trigger=1,trigger_side=0,objective=0,threshold=0) if self.objectives else dict(trigger=2,trigger_side=0,objective=-1,threshold=1)

    def node(self,path):
        node=self.expression
        for i in path.split('.')[1:]:node=node['children'][int(i)]
        return node

    def stash(self):
        if self.selected is None:return
        node=self.node(self.selected)
        if 'children' in node:
            node['operator']='all' if self.fields['kind'].get()=='ALL' else 'any'
        else:
            trigger=1 if self.fields['kind'].get()=='Objective controlled' else 2
            obj=self.widgets['objective'].current()
            changed=dict(trigger=trigger,trigger_side=('Allied','Axis').index(self.fields['side'].get()),
                objective=obj,threshold=self.fields['threshold'].get() if trigger==2 else 0)
            changed=normalize_expression(changed,len(self.objectives))
            node.clear();node.update(changed)

    def enable(self):
        kind=self.fields['kind'].get()
        for key,on,state in (('side',kind not in ('ALL','ANY'),'readonly'),
                             ('objective',kind=='Objective controlled','readonly'),
                             ('threshold',kind=='Losses reach threshold','normal')):
            self.widgets[key].config(state=state if on else 'disabled')

    def show(self,path):
        self.selected=path;node=self.node(path)
        group='children' in node
        self.widgets['kind'].config(values=('ALL','ANY') if group else
            (('Objective controlled','Losses reach threshold') if self.objectives else ('Losses reach threshold',)))
        self.fields['kind'].set(node['operator'].upper() if group else
            'Objective controlled' if node['trigger']==1 else 'Losses reach threshold')
        self.fields['side'].set(('Allied','Axis')[node.get('trigger_side',0)])
        index=node.get('objective',0)
        if self.objectives:self.widgets['objective'].current(max(0,index))
        self.fields['threshold'].set(str(node.get('threshold',1) or 1));self.enable()

    def refresh(self,selected):
        from lib.battle_plans import _condition_label
        self.selected=None
        self.tree.delete(*self.tree.get_children())
        def insert(node,path,parent):
            label=node['operator'].upper() if 'children' in node else _condition_label(node,self.objectives)
            self.tree.insert(parent,'end',iid=path,text=label,open=True)
            for i,c in enumerate(node.get('children',[])):insert(c,path+'.'+str(i),path)
        insert(self.expression,'0','')
        self.tree.selection_set(selected);self.show(selected)

    def select(self,event=None):
        chosen=self.tree.selection()
        if not chosen or chosen[0]==self.selected:return
        try:self.stash()
        except ValueError as exc:
            if self.selected:self.tree.selection_set(self.selected)
            messagebox.showerror('Invalid Condition',str(exc),parent=self);return
        self.refresh(chosen[0])

    def parent_group(self):
        path=self.selected or '0'
        return path if 'children' in self.node(path) else path.rsplit('.',1)[0]

    def add(self,node):
        try:self.stash()
        except ValueError as exc:
            messagebox.showerror('Invalid Condition',str(exc),parent=self);return
        path=self.parent_group();children=self.node(path)['children']
        children.append(node);self.refresh(path+'.'+str(len(children)-1))

    def add_leaf(self):self.add(self.default_leaf())
    def add_group(self,operator):self.add(dict(operator=operator,children=[self.default_leaf()]))

    def remove(self):
        path=self.selected
        if not path or path=='0':return
        parent,index=path.rsplit('.',1)
        del self.node(parent)['children'][int(index)]
        self.refresh(parent)

    def submit(self):
        try:
            self.stash();expression=normalize_expression(self.expression,len(self.objectives))
        except ValueError as exc:
            messagebox.showerror('Invalid Conditions',str(exc),parent=self);return
        self.callback(expression);self.close()

    def close(self):
        self.destroy()
        if self.parent.winfo_exists():self.parent.grab_set()
