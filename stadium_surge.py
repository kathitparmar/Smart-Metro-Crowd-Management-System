import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import csv, math

BG='#0b1220'; PANEL='#172338'; TEXT='#e8f0fa'; MUTED='#9cb0c7'; ACCENT='#32c5ff'

class StadiumSurge(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('STADIUM SURGE | Metro Crowd Operations Simulator')
        self.geometry('1230x780'); self.minsize(980,650); self.configure(bg=BG)
        self.plan=[]; self.index=0; self.running=False; self.job=None
        style=ttk.Style(self); style.theme_use('clam')
        style.configure('TFrame',background=BG); style.configure('TLabel',background=BG,foreground=TEXT,font=('Segoe UI',10))
        style.configure('TButton',font=('Segoe UI',10,'bold'),padding=8)
        style.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=TEXT,rowheight=26)
        style.configure('Treeview.Heading',background='#23344e',foreground='white',font=('Segoe UI',10,'bold'))
        style.map('Treeview',background=[('selected','#235779')])
        self.build()

    def build(self):
        header=tk.Frame(self,bg=BG); header.pack(fill='x',padx=22,pady=(16,8))
        tk.Label(header,text='🚇  STADIUM SURGE',font=('Segoe UI',23,'bold'),bg=BG,fg=ACCENT).pack(side='left')
        tk.Label(header,text='Metro Crowd Operations • Simulation / Decision Support',bg=BG,fg=MUTED,font=('Segoe UI',11)).pack(side='right')
        top=tk.Frame(self,bg=BG); top.pack(fill='x',padx=20)
        inputs=tk.LabelFrame(top,text=' EVENT INPUTS ',bg=PANEL,fg=ACCENT,font=('Segoe UI',11,'bold'),padx=12,pady=9)
        inputs.pack(side='left',fill='x',expand=True,padx=(0,10))
        self.venue=tk.StringVar(value='Narendra Modi Stadium')
        self.att=tk.StringVar(value='50000'); self.share=tk.StringVar(value='35')
        self.end=tk.StringVar(value='22:30'); self.platform=tk.StringVar(value='700')
        fields=[('Venue',self.venue),('Attendance',self.att),('Metro users (%)',self.share),('Event end (HH:MM)',self.end),('Safe platform limit',self.platform)]
        for i,(name,var) in enumerate(fields):
            tk.Label(inputs,text=name,bg=PANEL,fg=TEXT).grid(row=i//3*2,column=i%3,sticky='w',padx=6,pady=(3,0))
            tk.Entry(inputs,textvariable=var,width=23,bg='#e8f0fa',fg='#111827').grid(row=i//3*2+1,column=i%3,sticky='ew',padx=6,pady=(0,5))
        for c in range(3):inputs.columnconfigure(c,weight=1)
        actions=tk.Frame(top,bg=BG);actions.pack(side='right',fill='y')
        for title,fn in [('Generate plan',self.generate),('▶ Play simulation',self.toggle),('Export CSV',self.export)]:
            tk.Button(actions,text=title,command=fn,bg='#116b91',fg='white',activebackground='#168bb6',relief='flat',width=19,pady=9).pack(pady=4)
        self.play_button=actions.winfo_children()[1]
        stats=tk.Frame(self,bg=BG);stats.pack(fill='x',padx=20,pady=12)
        self.stats={}
        for key in ['Time','Arrivals / min','Platform queue','Crowd status','Action']:
            frame=tk.Frame(stats,bg=PANEL,padx=14,pady=11);frame.pack(side='left',fill='both',expand=True,padx=4)
            tk.Label(frame,text=key.upper(),bg=PANEL,fg=MUTED,font=('Segoe UI',9,'bold')).pack(anchor='w')
            label=tk.Label(frame,text='—',bg=PANEL,fg=ACCENT,font=('Segoe UI',14,'bold'),wraplength=220,justify='left')
            label.pack(anchor='w',pady=(5,0));self.stats[key]=label
        tabs=ttk.Notebook(self);tabs.pack(fill='both',expand=True,padx=24,pady=(0,15))
        charttab=tk.Frame(tabs,bg=BG);plantab=tk.Frame(tabs,bg=BG);annctab=tk.Frame(tabs,bg=BG)
        tabs.add(charttab,text='  Crowd Forecast  ');tabs.add(plantab,text='  Minute-by-minute Plan  ');tabs.add(annctab,text='  Announcements  ')
        self.chart=tk.Canvas(charttab,bg=PANEL,highlightthickness=0);self.chart.pack(fill='both',expand=True,padx=8,pady=8)
        self.chart.bind('<Configure>',lambda e:self.draw())
        cols=('time','arrivals','queue','status','gates','train','action')
        self.table=ttk.Treeview(plantab,columns=cols,show='headings')
        widths=[85,100,100,100,80,95,380]
        for col,w in zip(cols,widths):self.table.heading(col,text=col.replace('_',' ').title());self.table.column(col,width=w,anchor='center' if col!='action' else 'w')
        sy=ttk.Scrollbar(plantab,orient='vertical',command=self.table.yview);self.table.configure(yscrollcommand=sy.set)
        sy.pack(side='right',fill='y');self.table.pack(fill='both',expand=True,padx=8,pady=8)
        self.lang=tk.StringVar(value='English')
        bar=tk.Frame(annctab,bg=BG);bar.pack(fill='x',padx=14,pady=12)
        tk.Label(bar,text='Announcement language:',bg=BG,fg=TEXT).pack(side='left')
        lang=ttk.Combobox(bar,textvariable=self.lang,values=['English','Hindi','Gujarati'],state='readonly',width=16)
        lang.pack(side='left',padx=10);lang.bind('<<ComboboxSelected>>',lambda e:self.announce())
        tk.Button(bar,text='Copy announcement',command=self.copy_announcement).pack(side='left')
        self.anntext=tk.Text(annctab,bg=PANEL,fg=TEXT,font=('Segoe UI',13),wrap='word',relief='flat',padx=20,pady=20)
        self.anntext.pack(fill='both',expand=True,padx=12,pady=(0,12))
        tk.Label(self,text='DEMO ONLY • Queue and train estimates are hypothetical. Real deployment requires validated capacity, infrastructure, operator approval and safety protocols.',bg=BG,fg=MUTED,font=('Segoe UI',9)).pack(pady=(0,10))
        self.generate()

    def generate(self):
        self.pause()
        try:
            attendance=int(self.att.get());share=float(self.share.get());capacity=int(self.platform.get())
            t0=datetime.strptime(self.end.get().strip(),'%H:%M')
            if not(100<=attendance<=1000000 and 0<share<=100 and 100<=capacity<=10000):raise ValueError
        except ValueError:
            messagebox.showerror('Invalid inputs','Enter valid attendance (100–1,000,000), metro percentage (0–100), safe platform limit (100–10,000), and end time HH:MM.');return
        # Normalized bell-shaped post-event arrivals, with a secondary late tail.
        weights=[0.78*math.exp(-0.5*((m-18)/11)**2)+0.22*math.exp(-0.5*((m-42)/16)**2) for m in range(91)]
        total=attendance*share/100;weight_sum=sum(weights)
        arrivals=[round(total*w/weight_sum) for w in weights]
        arrivals[-1]+=round(total)-sum(arrivals)
        queue=0;self.plan=[]
        for m,arr in enumerate(arrivals):
            # Fixed illustrative service assumptions, NOT live metro availability.
            trains=1 if m%6==0 else 0
            if m%6==0 and (queue+arr)>capacity*0.65:trains=2
            served=trains*850
            # Holding area prevents platform occupancy from exceeding the configured safe limit.
            waiting=max(0,queue+arr-served)
            platform_queue=min(waiting,capacity)
            held=max(0,waiting-capacity)
            queue=waiting
            ratio=platform_queue/capacity
            status='CRITICAL' if ratio>=.9 or held>capacity else 'HIGH' if ratio>=.65 else 'MODERATE' if ratio>=.35 else 'LOW'
            gates=6 if status=='CRITICAL' else 4 if status=='HIGH' else 3 if status=='MODERATE' else 2
            if held>0:action=f'Hold ~{held:,} outside platform; meter entry; request operator support'
            elif status=='CRITICAL':action='Restrict entry; dispatch control-room alert'
            elif status=='HIGH':action='Open additional approved gates; prepare train request'
            elif status=='MODERATE':action='Direct passengers to marked queues'
            else:action='Normal monitored boarding'
            self.plan.append(dict(time=(t0+timedelta(minutes=m)).strftime('%H:%M'),arrivals=arr,queue=platform_queue,held=held,status=status,gates=gates,trains=trains,action=action))
        for item in self.table.get_children():self.table.delete(item)
        for p in self.plan:self.table.insert('', 'end',values=(p['time'],p['arrivals'],p['queue'],p['status'],p['gates'],p['trains'],p['action']))
        self.index=0;self.update_stats();self.draw();self.announce()

    def update_stats(self):
        if not self.plan:return
        p=self.plan[self.index]
        for k,v in {'Time':p['time'],'Arrivals / min':f"{p['arrivals']:,}",'Platform queue':f"{p['queue']:,}",'Crowd status':p['status'],'Action':p['action']}.items():self.stats[k].configure(text=v,fg='#ff7373' if k=='Crowd status' and v=='CRITICAL' else ACCENT)
        children=self.table.get_children()
        if children:
            self.table.selection_set(children[self.index]);self.table.see(children[self.index])

    def draw(self):
        c=self.chart;c.delete('all')
        if not self.plan:return
        w=max(c.winfo_width(),400);h=max(c.winfo_height(),220)
        left=65;right=w-28;top=36;bottom=h-55
        c.create_text(left,15,text='Predicted platform queue by minute',anchor='w',fill=TEXT,font=('Segoe UI',13,'bold'))
        limit=int(self.platform.get());peak=max(limit,max(p['queue'] for p in self.plan),1)
        for i in range(5):
            y=bottom-(bottom-top)*i/4
            c.create_line(left,y,right,y,fill='#304057',dash=(3,5))
            c.create_text(left-10,y,text=str(round(peak*i/4)),anchor='e',fill=MUTED)
        coords=[]
        for i,p in enumerate(self.plan):coords.extend((left+(right-left)*i/90,bottom-(bottom-top)*p['queue']/peak))
        c.create_line(*coords,fill=ACCENT,width=3,smooth=True)
        for i in [0,15,30,45,60,75,90]:c.create_text(left+(right-left)*i/90,bottom+20,text=f'+{i}m',fill=MUTED)
        x=left+(right-left)*self.index/90
        c.create_line(x,top,x,bottom,fill='#ffb44a',dash=(4,4),width=2)
        c.create_text(right,17,text='Orange marker = current simulation minute',anchor='e',fill=MUTED)

    def toggle(self):
        if not self.plan:self.generate()
        if self.running:self.pause()
        else:self.running=True;self.play_button.configure(text='⏸ Pause simulation');self.tick()

    def tick(self):
        if not self.running:return
        self.update_stats();self.draw();self.announce()
        if self.index>=len(self.plan)-1:self.pause();return
        self.index+=1;self.job=self.after(450,self.tick)

    def pause(self):
        self.running=False
        if self.job is not None:self.after_cancel(self.job);self.job=None
        if hasattr(self,'play_button'):self.play_button.configure(text='▶ Play simulation')

    def announce(self):
        if not self.plan:return
        p=self.plan[self.index];venue=self.venue.get().strip();status=p['status']
        msgs={
            'English':f'Attention passengers near {venue}. Current crowd level: {status}. Please follow station staff instructions, use designated entry gates, and do not rush. Additional services are subject to metro control-room approval.',
            'Hindi':f'यात्रियों कृपया ध्यान दें। {venue} के पास वर्तमान भीड़ का स्तर: {status}। कृपया स्टेशन कर्मचारियों के निर्देशों का पालन करें, निर्धारित प्रवेश द्वारों का उपयोग करें और धक्का-मुक्की न करें। अतिरिक्त ट्रेन सेवाएँ नियंत्रण कक्ष की अनुमति पर निर्भर हैं।',
            'Gujarati':f'મુસાફરો કૃપા કરીને ધ્યાન આપો. {venue} નજીક હાલમાં ભીડનું સ્તર: {status}. કૃપા કરીને સ્ટેશન કર્મચારીઓની સૂચનાઓનું પાલન કરો, નિર્ધારિત પ્રવેશદ્વારોનો ઉપયોગ કરો અને ધક્કામુક્કી ન કરો. વધારાની ટ્રેન સેવા નિયંત્રણ કક્ષાની મંજૂરીને આધીન છે.'
        }
        self.anntext.delete('1.0','end');self.anntext.insert('1.0',msgs[self.lang.get()])

    def copy_announcement(self):
        self.clipboard_clear();self.clipboard_append(self.anntext.get('1.0','end-1c'))
        messagebox.showinfo('Copied','Announcement copied to clipboard.')

    def export(self):
        if not self.plan:return
        path=filedialog.asksaveasfilename(defaultextension='.csv',initialfile='stadium_surge_plan.csv',filetypes=[('CSV files','*.csv')])
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(self.plan[0].keys()));writer.writeheader();writer.writerows(self.plan)
        messagebox.showinfo('Export complete',f'Saved {len(self.plan)} minutes to:\n{path}')

if __name__=='__main__':
    StadiumSurge().mainloop()
