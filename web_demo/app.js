const list = document.querySelector("#list");
const feed = document.querySelector("#feed");
const search = document.querySelector("#search");
const form = document.querySelector("#form");
const input = document.querySelector("#text");
const status = document.querySelector("#chat-status");
let rows = [];
let renderedSignature = "";

function renderList(query = "") {
  const chats = [["claude_bot", rows.length ? "Conversación sincronizada" : "Esperando mensajes", "CB"]];
  list.replaceChildren();
  chats.filter((chat) => chat[0].toLowerCase().includes(query.toLowerCase())).forEach((chat) => {
    const item = document.createElement("article");
    item.className = "row active";
    const avatar = document.createElement("i");
    avatar.className = "avatar";
    avatar.textContent = chat[2];
    const details = document.createElement("div");
    const name = document.createElement("b");
    name.textContent = chat[0];
    const preview = document.createElement("small");
    preview.textContent = chat[1];
    details.append(name, preview);
    item.append(avatar, details);
    list.append(item);
  });
}

function renderMessages() {
  const signature = JSON.stringify(rows);
  if (signature === renderedSignature) return;
  renderedSignature = signature;
  feed.replaceChildren();
  const day = document.createElement("p");
  day.textContent = "CHAT COMPARTIDO · SINCRONIZADO";
  feed.append(day);
  rows.forEach((row) => {
    const bubble = document.createElement("article");
    bubble.className = `bubble ${row.bot === "codex_bot" ? "out" : "in"}`;
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${row.bot} · ${row.timestamp}`;
    bubble.append(meta, document.createTextNode(row.mensaje));
    feed.append(bubble);
  });
  feed.scrollTop = feed.scrollHeight;
}

async function synchronize() {
  try {
    const response = await fetch("/api/messages", { cache: "no-store" });
    if (!response.ok) throw new Error("No se pudo leer el historial");
    const payload = await response.json();
    rows = payload.messages;
    renderMessages();
    renderList(search.value);
    status.textContent = "● Sincronizado";
  } catch (_) {
    status.textContent = "● Sin conexión";
  }
}

search.addEventListener("input", (event) => renderList(event.target.value));
form.addEventListener("submit", (event) => event.preventDefault());
input.disabled = true;
input.placeholder = "El historial se actualiza automáticamente";
renderList();
synchronize();
window.setInterval(synchronize, 3000);