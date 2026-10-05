from pathlib import Path
from datetime import datetime, timezone
import random

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "projects"

PROJECTS = [
("neon-todo","Neon Todo","Website","A polished localStorage todo app.",{
"index.html":"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Neon Todo</title><link rel="stylesheet" href="style.css"></head><body><main><p>DAILY BUILD</p><h1>Neon Todo</h1><form id="form"><input id="input" placeholder="What needs doing?"><button>Add</button></form><div><button data-f="all">All</button><button data-f="active">Active</button><button data-f="done">Done</button></div><ul id="list"></ul></main><script src="app.js"></script></body></html>""",
"style.css":"""*{box-sizing:border-box}body{margin:0;min-height:100vh;background:#090b12;color:#f7f7fb;font:16px system-ui;display:grid;place-items:center;padding:24px}main{width:min(680px,100%);background:#111522;border:1px solid #252c40;border-radius:24px;padding:32px}p{color:#7df9a7;letter-spacing:2px;font-size:12px}h1{font-size:60px}form{display:flex;gap:10px}input{flex:1;padding:15px;border-radius:12px;border:1px solid #30384d;background:#0b0f19;color:white}button{padding:10px 14px;margin:4px;border:1px solid #30384d;border-radius:9px;background:#171d2c;color:white}ul{list-style:none;padding:0}li{padding:12px;border-bottom:1px solid #252c40}.done{text-decoration:line-through;opacity:.45}""",
"app.js":"""const k='todo',s=localStorage;let a=JSON.parse(s.getItem(k)||'[]'),f='all';function r(){list.innerHTML='';a.filter(x=>f==='all'||f==='done'&&x.d||f==='active'&&!x.d).forEach(x=>{let l=document.createElement('li');l.className=x.d?'done':'';l.innerHTML='<input type=checkbox '+(x.d?'checked':'')+'>'+x.t+' <button>×</button>';l.querySelector('input').onchange=()=>{x.d=!x.d;save()};l.querySelector('button').onclick=()=>{a=a.filter(y=>y!==x);save()};list.append(l)})}function save(){s.setItem(k,JSON.stringify(a));r()}form.onsubmit=e=>{e.preventDefault();if(input.value.trim()){a.push({t:input.value.trim(),d:false});input.value='';save()}};document.querySelectorAll('[data-f]').forEach(b=>b.onclick=()=>{f=b.dataset.f;r()});r();"""
}),
("reaction-game","Reaction Game","Game","Click the target as fast as possible after it appears.",{
"index.html":"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reaction Game</title><link rel="stylesheet" href="style.css"></head><body><main><p>MINI GAME</p><h1>Reaction Time</h1><p id="score">Press start.</p><button id="start">Start</button><div id="arena"><div id="target"></div></div></main><script src="game.js"></script></body></html>""",
"style.css":"""body{margin:0;background:#0b0b0d;color:#fff;font:16px system-ui;text-align:center;padding:40px}button{padding:12px 22px;border:0;border-radius:10px;background:#fff;font-weight:700}#arena{height:55vh;max-width:800px;margin:25px auto;border:1px solid #333;border-radius:20px;position:relative;background:#121216}#target{display:none;position:absolute;width:54px;height:54px;border-radius:50%;background:#ff5d8f;cursor:pointer}""",
"game.js":"""const a=document.querySelector('#arena'),t=document.querySelector('#target'),s=document.querySelector('#score'),b=document.querySelector('#start');let z=0;b.onclick=()=>{b.disabled=true;s.textContent='Wait...';setTimeout(()=>{t.style.left=Math.random()*(a.clientWidth-54)+'px';t.style.top=Math.random()*(a.clientHeight-54)+'px';t.style.display='block';z=performance.now();s.textContent='CLICK!'},700+Math.random()*2200)};t.onclick=()=>{s.textContent='Your reaction: '+Math.round(performance.now()-z)+' ms';t.style.display='none';b.disabled=false};"""
}),
("subnet-helper","Subnet Helper","Networking","Calculate IPv4 CIDR address counts and usable hosts.",{
"index.html":"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Subnet Helper</title><link rel="stylesheet" href="style.css"></head><body><main><p>NETWORKING LAB</p><h1>Subnet Helper</h1><input id="ip" value="192.168.1.0"><input id="cidr" type="number" min="0" max="32" value="24"><button id="go">Calculate</button><pre id="out"></pre></main><script src="app.js"></script></body></html>""",
"style.css":"""body{margin:0;background:#0b0f12;color:#eaf7ef;font:16px system-ui;display:grid;place-items:center;min-height:100vh}main{width:min(680px,90%)}p{color:#63ff9a;letter-spacing:2px;font-size:12px}h1{font-size:52px}input{padding:12px;background:#111820;border:1px solid #28333d;border-radius:8px;color:white;margin:4px}button{padding:12px 18px;border:0;border-radius:8px;background:#63ff9a;font-weight:800}pre{white-space:pre-wrap;background:#111820;padding:20px;border-radius:12px}""",
"app.js":"""const ip=document.querySelector('#ip'),c=document.querySelector('#cidr'),o=document.querySelector('#out');go.onclick=()=>{let p=+c.value;if(p<0||p>32)return;let total=2**(32-p),usable=p>=31?total:Math.max(0,total-2);o.textContent='Network: '+ip.value+'/'+p+'\\\\nTotal addresses: '+total.toLocaleString()+'\\\\nUsable hosts: '+usable.toLocaleString()+'\\\\nHost bits: '+(32-p)};"""
}),
("quick-converter","Quick Converter","Utility","Convert length, weight and temperature units.",{
"index.html":"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Quick Converter</title><link rel="stylesheet" href="style.css"></head><body><main><p>UTILITY</p><h1>Quick Converter</h1><input id="v" type="number" value="10"><select id="u"><option value="km-mi">km → miles</option><option value="mi-km">miles → km</option><option value="kg-lb">kg → lb</option><option value="lb-kg">lb → kg</option><option value="c-f">°C → °F</option><option value="f-c">°F → °C</option></select><h2 id="r">—</h2></main><script src="app.js"></script></body></html>""",
"style.css":"""body{margin:0;min-height:100vh;display:grid;place-items:center;background:#111;color:white;font:16px system-ui}main{width:min(650px,90%)}p{color:#ffcf66;letter-spacing:2px}h1{font-size:56px}input,select{padding:15px;margin:5px;border-radius:10px;border:1px solid #333;background:#191919;color:white}h2{font-size:36px;color:#ffcf66}""",
"app.js":"""const v=document.querySelector('#v'),u=document.querySelector('#u'),r=document.querySelector('#r');function calc(){let x=+v.value,n=x;if(u.value==='km-mi')n=x*.621371;if(u.value==='mi-km')n=x/.621371;if(u.value==='kg-lb')n=x*2.20462;if(u.value==='lb-kg')n=x/2.20462;if(u.value==='c-f')n=x*9/5+32;if(u.value==='f-c')n=(x-32)*5/9;r.textContent=Number.isFinite(n)?n.toFixed(3):'—'}v.oninput=calc;u.onchange=calc;calc();"""
}),
("typing-test","Typing Speed Test","Mini App","A 30-second browser typing speed test.",{
"index.html":"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Typing Test</title><link rel="stylesheet" href="style.css"></head><body><main><p>30 SECOND CHALLENGE</p><h1>Typing Test</h1><blockquote>The quick brown fox jumps over the lazy dog while developers ship useful things.</blockquote><textarea id="text" disabled placeholder="Press Start..."></textarea><button id="start">Start</button><h2 id="result"></h2></main><script src="app.js"></script></body></html>""",
"style.css":"""body{margin:0;background:#0c0d10;color:#f2f2f2;font:17px system-ui;display:grid;place-items:center;min-height:100vh}main{width:min(800px,90%)}p{color:#8ab4ff;letter-spacing:2px;font-size:12px}h1{font-size:58px}blockquote{padding:20px;border-left:3px solid #8ab4ff;color:#b7bdca}textarea{width:100%;height:150px;box-sizing:border-box;background:#15171c;border:1px solid #2b2f38;color:white;padding:15px;border-radius:12px}button{margin-top:14px;padding:12px 20px;border:0;border-radius:9px;background:#8ab4ff;font-weight:800}""",
"app.js":"""const t=document.querySelector('#text'),b=document.querySelector('#start'),r=document.querySelector('#result');b.onclick=()=>{t.disabled=false;t.value='';t.focus();b.disabled=true;r.textContent='30 seconds...';setTimeout(()=>{t.disabled=true;let w=t.value.trim().split(/\\\\s+/).filter(Boolean).length;r.textContent='≈ '+Math.round(w*2)+' WPM';b.disabled=false},30000)};"""
})
]

def main():
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    random.seed(date)
    slug,title,kind,description,files=random.choice(PROJECTS)
    folder=OUT/(date+"-"+slug)
    if folder.exists(): return
    folder.mkdir(parents=True)
    for name,content in files.items():
        (folder/name).write_text(content,encoding="utf-8")
    (folder/"README.md").write_text(
        "# "+title+"\\n\\n**Type:** "+kind+"\\n\\n"+description+
        "\\n\\nGenerated automatically by Jojo Daily Bot on "+date+".\\n\\nOpen index.html in a browser.\\n",
        encoding="utf-8")
    index=OUT/"README.md"
    old=index.read_text(encoding="utf-8") if index.exists() else "# Daily Projects\\n"
    entry="- **"+date+"** — ["+title+"]("+folder.name+"/) · "+kind+"\\n"
    index.write_text(old.rstrip()+"\\n\\n"+entry,encoding="utf-8")

if __name__=="__main__":
    main()
