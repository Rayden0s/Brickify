from flask import Flask, jsonify, send_from_directory, request, Response
import os

app = Flask(__name__)
BASE = os.path.dirname(__file__)
MUSIC = os.path.join(BASE, "music")
STATIC = os.path.join(BASE, "static")
os.makedirs(MUSIC, exist_ok=True)
os.makedirs(STATIC, exist_ok=True)

# ---------------- BACKEND ----------------

def scan_playlists():
    data = {}
    for folder in os.listdir(MUSIC):
        p = os.path.join(MUSIC, folder)
        if os.path.isdir(p):
            songs = [f for f in os.listdir(p)
                     if f.lower().endswith((".mp3",".wav",".ogg",".flac"))]
            if songs:
                data[folder] = songs
    return data

@app.route("/api/playlists")
def playlists():
    return jsonify(scan_playlists())

@app.route("/music/<pl>/<song>")
def music(pl, song):
    return send_from_directory(os.path.join(MUSIC, pl), song)

@app.route("/art/<pl>")
def art(pl):
    for f in ("cover.jpg","folder.jpg","cover.png"):
        p = os.path.join(MUSIC, pl, f)
        if os.path.exists(p):
            return send_from_directory(os.path.join(MUSIC, pl), f)
    return "", 404

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    playlist = request.form["playlist"]
    dest = os.path.join(MUSIC, playlist)
    os.makedirs(dest, exist_ok=True)
    for f in files:
        f.save(os.path.join(dest, f.filename))
    return "", 204

# ---------------- PWA STATIC ----------------
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/service-worker.js')
def sw():
    return send_from_directory('static', 'service-worker.js')

@app.route('/static/<path:p>')
def static_files(p):
    return send_from_directory('static', p)

# ---------------- FRONTEND ----------------

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Brickify</title>
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#FF0000">
<script>
if('serviceWorker' in navigator){
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').then(reg=>{
      console.log("SW registered", reg);
    });
  });
}
</script>
<style>
body{margin:0;background:#111;color:white;font-family:Arial;display:flex;flex-direction:column;height:100vh;}
#top{display:flex;justify-content:space-between;align-items:center;padding:12px;background:#222;}
#logo {background:#FF0000;color:white;font-weight:bold;font-size:22px;padding:6px 12px;border-radius:8px;display:flex;align-items:center;gap:6px;}
#logo::before {content:"▶";font-size:18px;}
#moreBtn{width:60px;height:60px;font-size:30px;border:none;border-radius:12px;background:#333;color:white;}
#player{flex:1;display:flex;flex-direction:row;padding:12px;gap:24px;overflow:hidden;}
#album{width:280px;height:280px;background:#333;border-radius:18px;flex-shrink:0;}
#info{flex:1;display:flex;flex-direction:column;}
#title{font-size:22px;margin-bottom:8px;}
#time{margin-bottom:8px;}
button{background:#333;color:white;border:none;border-radius:12px;padding:12px;margin:4px;font-size:20px;cursor:pointer;}
button:hover{background:#1DB954;color:black;}
.song{display:flex;justify-content:space-between;align-items:center;padding:6px 0;}
.menu{display:flex;gap:8px;}
#controls{display:flex;justify-content:center;align-items:center;gap:12px;padding:8px;flex-wrap:wrap;}
#seek,#vol{width:100%;}
#menu{position:absolute;top:72px;right:12px;width:300px;background:#222;border-radius:18px;padding:12px;display:none;flex-direction:column;max-height:70%;overflow:auto;}
#queuePanel{position:fixed;bottom:-60%;left:0;width:100%;max-height:60%;background:#222;border-top-left-radius:18px;border-top-right-radius:18px;padding:12px;overflow:auto;transition:bottom 0.3s;}
#queuePanel.show{bottom:0;}
.song button{padding:8px;font-size:18px;}
ul{list-style:none;padding:0;margin:0;}
li{padding:6px 0;display:flex;justify-content:space-between;align-items:center;}
</style>
</head>
<body>

<div id="top">
  <div id="logo">Brickify</div>
  <button id="moreBtn">⋮</button>
</div>

<div id="player">
  <div id="album"></div>
  <div id="info">
    <h3 id="title">Nothing Playing</h3>
    <div id="time">0:00 / 0:00</div>
    <input id="seek" type="range" min="0" max="100">
    <div id="controls">
      <button id="prev">⏮</button>
      <button id="play">▶</button>
      <button id="next">⏭</button>
      <button id="shuffleBtn">🔀</button>
      <button id="loopBtn">🔁</button>
      <input id="vol" type="range" min="0" max="1" step="0.01" value="0.5">
    </div>
  </div>
</div>

<button onclick="addFolder()">Add Folder</button>

<div id="menu">
  <h4>Playlists</h4>
  <select id="playlist"></select>
  <div id="songs"></div>
</div>

<button id="queueBtn">Queue 🎵</button>
<div id="queuePanel"><h4>Queue</h4><ul id="queue"></ul></div>

<script>
const audio = new Audio();
let playlists={},currentPl="",currentIdx=0,queue=[],allSongs=[];
const playlistEl=document.getElementById("playlist");
const songsEl=document.getElementById("songs");
const art=document.getElementById("album");
const titleEl=document.getElementById("title");
const timeEl=document.getElementById("time");
const seek=document.getElementById("seek");
const vol=document.getElementById("vol");
const play=document.getElementById("play");
const prev=document.getElementById("prev");
const next=document.getElementById("next");
const shuffleBtn=document.getElementById("shuffleBtn");
const loopBtn=document.getElementById("loopBtn");
const menu=document.getElementById("menu");
const moreBtn=document.getElementById("moreBtn");
const queueBtn=document.getElementById("queueBtn");
const queuePanel=document.getElementById("queuePanel");
const queueEl=document.getElementById("queue");

let shuffleMode=0; // 0=off, 1=shuffle playlist, 2=shuffle all songs
let loopMode="off"; // off, song, playlist

moreBtn.onclick=()=>{menu.style.display=menu.style.display==="flex"?"none":"flex";}
queueBtn.onclick=()=>{queuePanel.classList.toggle("show");}

shuffleBtn.onclick = () => {
  shuffleMode = (shuffleMode + 1) % 3; 
  if(shuffleMode===0){ shuffleBtn.style.background="#333"; shuffleBtn.textContent="🔀"; }
  else{ shuffleBtn.style.background="#1DB954"; }
  if(shuffleMode===1) shuffleBtn.textContent="🔀 (Playlist)";
  else if(shuffleMode===2) shuffleBtn.textContent="🔀 (All)";
};

loopBtn.onclick=()=>{
  if(loopMode==="off"){ loopMode="playlist"; loopBtn.style.background="#1DB954"; loopBtn.textContent="🔁"; }
  else if(loopMode==="playlist"){ loopMode="song"; loopBtn.textContent="🔂"; }
  else{ loopMode="off"; loopBtn.style.background="#333"; loopBtn.textContent="🔁"; }
};

fetchPlaylists();
playlistEl.onchange=loadPlaylist;

function fetchPlaylists(){
 fetch("/api/playlists").then(r=>r.json()).then(d=>{
  playlists=d;
  playlistEl.innerHTML="";
  allSongs=[]; 
  for(let p in d){
    playlistEl.add(new Option(p,p));
    d[p].forEach(s=>allSongs.push({pl:p,song:s}));
  }
  loadPlaylist();
 });
}

function loadPlaylist(){
 currentPl=playlistEl.value;
 songsEl.innerHTML="";
 playlists[currentPl].forEach((s,i)=>{
  let div=document.createElement("div");
  div.className="song";
  div.innerHTML=`${s}<div class="menu">
     <button onclick="playSong(${i})">▶ Play</button>
     <button onclick="addQueue('${s}')">➕</button>
   </div>`;
  songsEl.appendChild(div);
 });
}

function playSong(i){
 currentIdx=i;
 const s=playlists[currentPl][i];
 audio.src=`/music/${currentPl}/${s}`;
 art.style.backgroundImage="url('/art/"+currentPl+"')";
 art.style.backgroundSize="cover";
 titleEl.textContent=s;
 audio.play();
 play.textContent="⏸";
}

function addQueue(s){
 queue.push({pl:currentPl,song:s});
 renderQueue();
}

function renderQueue(){
 queueEl.innerHTML="";
 queue.forEach((q,i)=>{
  let li=document.createElement("li");
  li.innerHTML=`${q.song} <button onclick="playFromQueue(${i})">▶</button>`;
  queueEl.appendChild(li);
 });
}

function playFromQueue(i){
 const q=queue.splice(i,1)[0];
 audio.src=`/music/${q.pl}/${q.song}`;
 titleEl.textContent=q.song;
 audio.play();
 renderQueue();
}

play.onclick=()=>audio.paused?(audio.play(),play.textContent="⏸"):(audio.pause(),play.textContent="▶");
prev.onclick=()=>playSong(Math.max(0,currentIdx-1));
next.onclick=nextTrack;

function nextTrack(){
 if(queue.length){ playFromQueue(0); }
 else if(shuffleMode===1){
  let r=playlists[currentPl][Math.floor(Math.random()*playlists[currentPl].length)];
  currentIdx=playlists[currentPl].indexOf(r);
  playSong(currentIdx);
 } else if(shuffleMode===2){
  let r=allSongs[Math.floor(Math.random()*allSongs.length)];
  currentPl=r.pl;
  currentIdx=playlists[currentPl].indexOf(r.song);
  playSong(currentIdx);
 } else {
  currentIdx++;
  if(currentIdx<playlists[currentPl].length) playSong(currentIdx);
  else if(loopMode==="playlist") playSong(0);
 }
 renderQueue();
}

audio.onended=()=>{
  if(loopMode==="song") audio.currentTime=0, audio.play();
  else nextTrack();
};

audio.ontimeupdate=()=>{
 seek.value=audio.currentTime/audio.duration*100||0;
 let min=Math.floor(audio.currentTime/60);
 let sec=Math.floor(audio.currentTime%60).toString().padStart(2,"0");
 let durMin=Math.floor(audio.duration/60)||0;
 let durSec=Math.floor(audio.duration%60).toString().padStart(2,"0");
 timeEl.textContent=`${min}:${sec} / ${durMin}:${durSec}`;
};

seek.oninput=()=>audio.currentTime=seek.value/100*audio.duration;
vol.oninput=e=>audio.volume=e.target.value;

function addFolder(){
 let i=document.createElement("input");
 i.type="file"; i.webkitdirectory=true; i.multiple=true;
 i.onchange=()=>{
  let data=new FormData();
  data.append("playlist",prompt("Playlist name"));
  [...i.files].forEach(f=>data.append("files",f));
  fetch("/upload",{method:"POST",body:data}).then(fetchPlaylists);
 };
 i.click();
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")

if __name__ == "__main__":
    app.run(debug=True)
