const token = document.body.dataset.token;
const state = {projects: [], sections: [], currentId: null, gallery: [], galleryChanged: false, videos: [], videosChanged: false, coverFile: null, coverObjectUrl: null, dirty: false};
const el = (id) => document.getElementById(id);
const projectList = el("projectList");
const form = el("projectForm");
const galleryList = el("galleryList");
const videoList = el("videoList");
const linksList = el("linksList");
const status = el("status");

function localAssetUrl(path) { return path ? `/portfolio-file/${path}` : ""; }
function setStatus(message, type = "") { status.textContent = message; status.className = `status ${type}`.trim(); }
function markDirty() { state.dirty = true; setStatus("Unsaved changes", "pending"); }
function clearDirty(message = "") { state.dirty = false; setStatus(message, message ? "success" : ""); }
function askBeforeDiscarding() { return !state.dirty || window.confirm("Discard the unsaved changes in this form?"); }
function escapeHtml(value) { const node = document.createElement("div"); node.textContent = value || ""; return node.innerHTML; }

function renderProjectList() {
  projectList.replaceChildren();
  const grouped = new Map(state.sections.map((section) => [section.value, []]));
  state.projects.forEach((project) => {
    if (!grouped.has(project.section)) grouped.set(project.section, []);
    grouped.get(project.section).push(project);
  });
  state.sections.forEach((section) => {
    const projects = grouped.get(section.value) || [];
    if (!projects.length) return;
    const group = document.createElement("div");
    group.className = "project-group";
    const heading = document.createElement("p");
    heading.className = "project-group-title";
    heading.textContent = `${section.en} / ${section.zh}`;
    group.append(heading);
    projects.forEach((project) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `project-item${project.id === state.currentId ? " active" : ""}`;
      button.innerHTML = `<span>${escapeHtml(project.title.en || project.title.zh)}</span><small>${escapeHtml(project.year)}</small>`;
      button.addEventListener("click", () => selectProject(project.id));
      group.append(button);
    });
    projectList.append(group);
  });
}

function populateSectionSelect() {
  el("section").replaceChildren(...state.sections.map((section) => {
    const option = document.createElement("option");
    option.value = section.value;
    option.textContent = `${section.en} / ${section.zh}`;
    return option;
  }));
}

function resetMediaObjectUrls() {
  state.gallery.forEach((item) => { if (item.objectUrl) URL.revokeObjectURL(item.objectUrl); });
  state.videos.forEach((item) => { if (item.objectUrl) URL.revokeObjectURL(item.objectUrl); });
  if (state.coverObjectUrl) URL.revokeObjectURL(state.coverObjectUrl);
  state.coverObjectUrl = null;
}

function selectProject(projectId, force = false) {
  if (!force && !askBeforeDiscarding()) return;
  state.settingsMode=false; el("settingsEditor").hidden=true; form.hidden=false;
  resetMediaObjectUrls();
  const project = state.projects.find((item) => item.id === projectId);
  if (!project) return;
  state.currentId = project.id;
  state.coverFile = null;
  state.gallery = project.gallery.map((path) => ({kind: "existing", path}));
  state.galleryChanged = false;
  state.videos = (project.videos || []).map((video) => ({kind: "existing", ...video}));
  state.videosChanged = false;
  el("projectId").value = project.id;
  el("titleEn").value = project.title.en || "";
  el("titleZh").value = project.title.zh || "";
  el("year").value = project.year || "";
  el("month").value = project.month || "";
  el("section").value = project.section;
  ["role","discipline","metrics","date"].forEach(k=>["en","zh"].forEach(l=>el(k+(l==="en"?"En":"Zh")).value=project[k]?.[l]||""));
  fillAssetSelect(el("coverPath"),project.cover);fillAssetSelect(el("galleryExisting"),"");
  el("descriptionEn").value = project.description.en || "";
  el("descriptionZh").value = project.description.zh || "";
  el("editorMode").textContent = "EDIT PROJECT";
  el("editorTitle").textContent = project.title.en || project.title.zh || "Untitled project";
  el("deleteProjectButton").hidden = false;
  renderCover(project.cover);
  renderGallery();
  renderVideos();
  renderLinks(project.links || []);
  renderProjectList();
  clearDirty();
}

function newProject(force = false) {
  if (!force && !askBeforeDiscarding()) return;
  state.settingsMode=false; el("settingsEditor").hidden=true; form.hidden=false;
  resetMediaObjectUrls();
  state.currentId = null;
  state.coverFile = null;
  state.gallery = [];
  state.galleryChanged = false;
  state.videos = [];
  state.videosChanged = false;
  form.reset(); fillAssetSelect(el("coverPath"), "");fillAssetSelect(el("galleryExisting"),"");
  el("projectId").value = "";
  el("section").value = state.sections[0]?.value || "creative-direction";
  el("editorMode").textContent = "NEW PROJECT";
  el("editorTitle").textContent = "Untitled project";
  el("deleteProjectButton").hidden = true;
  renderCover("");
  renderGallery();
  renderVideos();
  renderLinks([]);
  renderProjectList();
  clearDirty();
}

function renderCover(existingPath = "") {
  const preview = el("coverPreview");
  preview.replaceChildren();
  let source = existingPath ? localAssetUrl(existingPath) : "";
  if (state.coverFile) {
    if (state.coverObjectUrl) URL.revokeObjectURL(state.coverObjectUrl);
    state.coverObjectUrl = URL.createObjectURL(state.coverFile);
    source = state.coverObjectUrl;
  }
  if (!source) {
    preview.className = "cover-preview empty";
    const text = document.createElement("span");
    text.textContent = "No cover selected";
    preview.append(text);
    return;
  }
  preview.className = "cover-preview";
  const image = document.createElement("img");
  image.src = source;
  image.alt = "Project cover preview";
  preview.append(image);
}

function imageSource(item) { return item.kind === "existing" ? localAssetUrl(item.path) : item.objectUrl; }
function renderGallery() {
  galleryList.replaceChildren();
  if (!state.gallery.length) {
    const empty = document.createElement("p"); empty.className = "empty-message"; empty.textContent = "No gallery images yet."; galleryList.append(empty); return;
  }
  state.gallery.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = "gallery-card"; card.draggable = true;
    card.innerHTML = `<div class="drag-handle" aria-hidden="true">⋮⋮</div><img src="${escapeHtml(imageSource(item))}" alt="Gallery image ${index + 1}"><div class="gallery-meta"><strong>${String(index + 1).padStart(2, "0")}</strong><span>${item.kind === "new" ? "New image" : "Existing image"}</span></div><div class="gallery-actions"><button type="button" class="icon-button move-up" aria-label="Move image up">↑</button><button type="button" class="icon-button move-down" aria-label="Move image down">↓</button><button type="button" class="icon-button remove-image" aria-label="Remove image from project">×</button></div>`;
    card.querySelector(".move-up").disabled = index === 0;
    card.querySelector(".move-down").disabled = index === state.gallery.length - 1;
    card.querySelector(".move-up").addEventListener("click", () => moveGallery(index, index - 1));
    card.querySelector(".move-down").addEventListener("click", () => moveGallery(index, index + 1));
    card.querySelector(".remove-image").addEventListener("click", () => removeGallery(index));
    card.addEventListener("dragstart", (event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", String(index)); card.classList.add("dragging"); });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
    card.addEventListener("dragover", (event) => event.preventDefault());
    card.addEventListener("drop", (event) => { event.preventDefault(); moveGallery(Number(event.dataTransfer.getData("text/plain")), index); });
    galleryList.append(card);
  });
}

function moveGallery(from, to) {
  if (from === to || from < 0 || to < 0 || from >= state.gallery.length || to >= state.gallery.length) return;
  const [item] = state.gallery.splice(from, 1); state.gallery.splice(to, 0, item); state.galleryChanged = true; markDirty(); renderGallery();
}
function removeGallery(index) {
  const [item] = state.gallery.splice(index, 1); if (item?.objectUrl) URL.revokeObjectURL(item.objectUrl); state.galleryChanged = true; markDirty(); renderGallery();
}

function videoSource(item) { return item.kind === "existing" ? localAssetUrl(item.src) : item.objectUrl; }
function renderVideos() {
  videoList.replaceChildren();
  if (!state.videos.length) {
    const empty = document.createElement("p"); empty.className = "empty-message"; empty.textContent = "No videos yet."; videoList.append(empty); return;
  }
  state.videos.forEach((item, index) => {
    const fragment = el("videoTemplate").content.cloneNode(true);
    const card = fragment.querySelector(".video-card");
    const video = card.querySelector("video");
    video.src = videoSource(item);
    if (item.kind === "existing" && item.poster) video.poster = localAssetUrl(item.poster);
    const posterLabel=document.createElement("label");posterLabel.textContent="Video poster / 视频封面";
    const posterSelect=document.createElement("select");fillAssetSelect(posterSelect,item.poster);posterSelect.onchange=()=>{item.poster=posterSelect.value;video.poster=localAssetUrl(item.poster);state.videosChanged=true;markDirty()};posterLabel.append(posterSelect);card.querySelector(".video-fields").append(posterLabel);
    const titleEn = card.querySelector('[data-field="videoTitleEn"]');
    const titleZh = card.querySelector('[data-field="videoTitleZh"]');
    titleEn.value = item.title?.en || "";
    titleZh.value = item.title?.zh || "";
    const updateTitle = () => {
      item.title = {en: titleEn.value, zh: titleZh.value};
      state.videosChanged = true;
      markDirty();
    };
    titleEn.addEventListener("input", updateTitle);
    titleZh.addEventListener("input", updateTitle);
    card.querySelector(".video-up").disabled = index === 0;
    card.querySelector(".video-down").disabled = index === state.videos.length - 1;
    card.querySelector(".video-up").addEventListener("click", () => moveVideo(index, index - 1));
    card.querySelector(".video-down").addEventListener("click", () => moveVideo(index, index + 1));
    card.querySelector(".video-remove").addEventListener("click", () => removeVideo(index));
    card.addEventListener("dragstart", (event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", String(index)); card.classList.add("dragging"); });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
    card.addEventListener("dragover", (event) => event.preventDefault());
    card.addEventListener("drop", (event) => { event.preventDefault(); moveVideo(Number(event.dataTransfer.getData("text/plain")), index); });
    videoList.append(fragment);
  });
}

function moveVideo(from, to) {
  if (from === to || from < 0 || to < 0 || from >= state.videos.length || to >= state.videos.length) return;
  const [item] = state.videos.splice(from, 1); state.videos.splice(to, 0, item); state.videosChanged = true; markDirty(); renderVideos();
}
function removeVideo(index) {
  const [item] = state.videos.splice(index, 1); if (item?.objectUrl) URL.revokeObjectURL(item.objectUrl); state.videosChanged = true; markDirty(); renderVideos();
}

function addLink(link = {}) {
  const fragment = el("linkTemplate").content.cloneNode(true);
  const row = fragment.querySelector(".link-row");
  row.querySelector('[data-field="labelEn"]').value = link.label?.en || "";
  row.querySelector('[data-field="labelZh"]').value = link.label?.zh || "";
  row.querySelector('[data-field="url"]').value = link.url || "";
  row.querySelector(".remove-link").addEventListener("click", () => { row.remove(); markDirty(); });
  row.querySelectorAll("input").forEach((input) => input.addEventListener("input", markDirty));
  linksList.append(row);
}
function renderLinks(links) { linksList.replaceChildren(); links.forEach(addLink); if (!links.length) addLink(); }
function collectLinks() {
  return [...linksList.querySelectorAll(".link-row")].map((row) => ({label: {en: row.querySelector('[data-field="labelEn"]').value.trim(), zh: row.querySelector('[data-field="labelZh"]').value.trim()}, url: row.querySelector('[data-field="url"]').value.trim()})).filter((link) => link.url);
}

async function saveProject() {
  if(state.settingsMode)return saveSettings();
  if (!form.reportValidity()) return;
  const titleEn = el("titleEn").value.trim(); const titleZh = el("titleZh").value.trim();
  if (!titleEn && !titleZh) { setStatus("Please enter a project title.", "error"); return; }
  if (!state.currentId && !state.coverFile && !el("coverPath").value) { setStatus("Please choose a cover image for the new project.", "error"); return; }
  const payload = {id: state.currentId, title: {en: titleEn, zh: titleZh}, year: el("year").value.trim(), month: el("month").value, section: el("section").value, description: {en: el("descriptionEn").value.trim(), zh: el("descriptionZh").value.trim()}, links: collectLinks(), galleryChanged: state.galleryChanged, gallery: state.gallery.map((item) => item.kind === "existing" ? {kind: "existing", path: item.path} : {kind: "new", key: item.key}), videosChanged: state.videosChanged, videos: state.videos.map((item) => item.kind === "existing" ? {kind: "existing", src: item.src, poster: item.poster, webm: item.webm, title: item.title} : {kind: "new", key: item.key, title: item.title, poster:item.poster})};
  ["role","discipline","metrics","date"].forEach(k=>payload[k]={en:el(k+"En").value,zh:el(k+"Zh").value});
  payload.coverPath=el("coverPath").value;
  const body = new FormData(); body.append("payload", JSON.stringify(payload));
  if (state.coverFile) body.append("cover", state.coverFile, state.coverFile.name);
  state.gallery.forEach((item) => { if (item.kind === "new") body.append(`gallery_${item.key}`, item.file, item.file.name); });
  state.videos.forEach((item) => { if (item.kind === "new") body.append(`video_${item.key}`, item.file, item.file.name); });
  setStatus("Saving…", "pending"); el("saveButton").disabled = true;
  try {
    const response = await fetch("/api/projects/save", {method: "POST", headers: {"X-Portfolio-Token": token}, body});
    const result = await response.json(); if (!response.ok || !result.ok) throw new Error(result.error || "Could not save the project.");
    await loadProjects(result.project.id); clearDirty("Saved. Click Build Portfolio to update the preview.");
  } catch (error) { setStatus(error.message, "error"); } finally { el("saveButton").disabled = false; }
}

async function deleteProject() {
  if (!state.currentId) return;
  const project = state.projects.find((item) => item.id === state.currentId);
  const title = project?.title?.en || project?.title?.zh || state.currentId;
  const confirmed = window.confirm(`Delete “${title}” from the portfolio?\n\nIts image and video files will stay on this Mac, and a content backup will be created. This project's unsaved form changes will be discarded.`);
  if (!confirmed) return;
  setStatus("Removing project…", "pending");
  el("deleteProjectButton").disabled = true;
  try {
    const response = await fetch("/api/projects/delete", {method: "POST", headers: {"Content-Type": "application/json", "X-Portfolio-Token": token}, body: JSON.stringify({id: state.currentId})});
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || "Could not delete the project.");
    state.currentId = null;
    state.dirty = false;
    await loadProjects();
    setStatus("Project removed. Build Portfolio to update the preview. Media files were kept.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    el("deleteProjectButton").disabled = false;
  }
}

async function buildPortfolio() {
  if (state.dirty) { setStatus("Save this project before building the portfolio.", "error"); return; }
  setStatus("Building portfolio…", "pending"); el("buildButton").disabled = true;
  try {
    const response = await fetch("/api/build", {method: "POST", headers: {"X-Portfolio-Token": token}});
    const result = await response.json(); if (!response.ok || !result.ok) throw new Error(result.error || "Build failed.");
    el("previewButton").href = result.previewUrl; setStatus("Build complete. Local Preview is ready.", "success");
  } catch (error) { setStatus(error.message, "error"); } finally { el("buildButton").disabled = false; }
}

async function loadProjects(preferredId = null) {
  const settingsResponse=await fetch("/api/settings"); const settingsResult=await settingsResponse.json();state.settings=settingsResult.settings;state.assets=settingsResult.assets;
  const response = await fetch("/api/projects"); const result = await response.json();
  state.projects = result.projects; state.sections = result.sections; el("previewButton").href = result.previewUrl; populateSectionSelect();
  const nextId = preferredId || state.currentId || state.projects[0]?.id; if (nextId) selectProject(nextId, true); else newProject(true);
}

el("coverInput").addEventListener("change", (event) => { const [file] = event.target.files; if (!file) return; state.coverFile = file; renderCover(state.projects.find((item) => item.id === state.currentId)?.cover || ""); markDirty(); });
el("galleryInput").addEventListener("change", (event) => { [...event.target.files].forEach((file) => { const key = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`; state.gallery.push({kind: "new", key, file, objectUrl: URL.createObjectURL(file)}); }); event.target.value = ""; state.galleryChanged = true; markDirty(); renderGallery(); });
el("videoInput").addEventListener("change", (event) => { [...event.target.files].forEach((file) => { const key = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`; const title = file.name.replace(/\.[^.]+$/, ""); state.videos.push({kind: "new", key, file, objectUrl: URL.createObjectURL(file), title: {en: title, zh: title}}); }); event.target.value = ""; state.videosChanged = true; markDirty(); renderVideos(); });
form.addEventListener("submit", (event) => { event.preventDefault(); saveProject(); });
form.querySelectorAll("input:not([type=file]), textarea, select").forEach((input) => { input.addEventListener("input", () => { if (input.id === "titleEn" || input.id === "titleZh") el("editorTitle").textContent = el("titleEn").value || el("titleZh").value || "Untitled project"; markDirty(); }); input.addEventListener("change", markDirty); });
el("newProjectButton").addEventListener("click", () => newProject());
el("addLinkButton").addEventListener("click", () => { addLink(); markDirty(); });
el("saveButton").addEventListener("click", saveProject);
el("buildButton").addEventListener("click", buildPortfolio);
el("deleteProjectButton").addEventListener("click", deleteProject);
window.addEventListener("beforeunload", (event) => { if (!state.dirty) return; event.preventDefault(); event.returnValue = ""; });
loadProjects().catch((error) => setStatus(error.message, "error"));

function fillAssetSelect(select, selected) {
  select.replaceChildren();
  ["",...state.assets||[]].forEach(path=>{const option=document.createElement("option");option.value=path;option.textContent=path||"Choose image / 选择图片";select.append(option)});
  select.value=selected||"";
}
el("coverPath").addEventListener("change",()=>{state.coverFile=null;renderCover(el("coverPath").value);markDirty()});
el("year").addEventListener("change",syncDate);el("month").addEventListener("change",syncDate);
function syncDate(){const y=el("year").value,m=Number(el("month").value);if(y&&m){el("dateEn").value=new Date(2000,m-1).toLocaleString("en",{month:"long"})+" "+y;el("dateZh").value=y+" 年 "+m+" 月"}}
function settingsFields(value, container, prefix="") {
 Object.entries(value).forEach(([key,v])=>{
  if(key==="id")return;
  const names={en:"English",zh:"中文",role:"Role / 角色说明",cover:"Cover / 封面",wordmark:"Name / 网站名称",years:"Years / 年份",portfolio:"Portfolio label / 作品集标签",selectedWork:"Section heading / 栏目标题",photoSeries:"Photography label / 摄影系列标签",photoPlaceholder:"Empty description / 空简介提示",previousPage:"Previous page / 上一页",nextPage:"Next page / 下一页",homeImage:"Home background / 首页背景",portrait:"Portrait / 关于页照片",tagline:"Tagline / 标语",bio:"Biography / 简介",url:"Link address / 链接地址",label:"Link text / 链接文字",groups:"Category names / 分类名称",children:"Subcategories / 子分类",labels:"Interface text / 界面文字",links:"Contact links / 联系方式",home:"Home / 首页",about:"About / 关于",back:"Back / 返回",next:"Next project / 下个项目",previous:"Previous project / 上个项目",menu:"Menu / 菜单",intro:"Introduction / 首页介绍",selected:"Home title / 首页标题",images:"Images / 图片",films:"Films / 视频",empty:"Empty heading / 空栏目标题",emptyText:"Empty description / 空栏目说明",visit:"Project link / 项目链接",skip:"Skip link / 跳转内容",prevMedia:"Previous media / 上一组媒体",nextMedia:"Next media / 下一组媒体",image:"Image / 图片标签",film:"Film / 视频标签"};
  const name=names[key]||state.sections.find(s=>s.value===key)?.en||key;
  if(v&&typeof v==="object"){
   const block=document.createElement("details");block.open=prefix==="";const title=document.createElement("summary");
   title.textContent=v.id?(state.sections.find(s=>s.value===v.id)?.en||v.en||v.id):({site:"Navigation & interface / 导航及界面文字",categoryCards:"Category cards / 子分类封面与角色",pages:"Home & About / 首页与关于"}[key]||name);block.append(title);settingsFields(v,block,name);container.append(block);return;
  }
  const label=document.createElement("label");label.textContent=name;
  if(["cover","homeImage","portrait"].includes(key)){
   const select=document.createElement("select");fillAssetSelect(select,v);const image=document.createElement("img");image.className="settings-image";image.src=localAssetUrl(v);
   select.onchange=()=>{value[key]=select.value;image.src=localAssetUrl(select.value);markDirty()};
   const upload=document.createElement("input");upload.type="file";upload.accept="image/jpeg,image/png,image/webp";
   upload.onchange=async()=>{if(!upload.files[0])return;try{const body=new FormData();body.append("image",upload.files[0]);const r=await fetch("/api/settings/image",{method:"POST",headers:{"X-Portfolio-Token":token},body});const result=await r.json();if(!r.ok)throw Error(result.error);state.assets.push(result.path);fillAssetSelect(select,result.path);select.onchange()}catch(e){setStatus(e.message,"error")}};
   label.append(select,image,upload);
  }else{const input=document.createElement("textarea");input.rows=String(v).length>100?4:2;input.value=v;input.oninput=()=>{value[key]=input.value;markDirty()};label.append(input)}
  container.append(label);
 });
}
el("siteSettingsButton").addEventListener("click",async()=>{
 if(!askBeforeDiscarding())return;
 const r=await fetch("/api/settings");const result=await r.json();state.settings=result.settings;state.assets=result.assets;state.settingsMode=true;form.hidden=true;el("settingsEditor").hidden=false;el("settingsEditor").replaceChildren();settingsFields(state.settings,el("settingsEditor"));el("editorTitle").textContent="Website & category settings / 网站与分类";el("editorMode").textContent="EDIT WEBSITE";el("deleteProjectButton").hidden=true;clearDirty();
});
async function saveSettings(){try{const r=await fetch("/api/settings",{method:"POST",headers:{"Content-Type":"application/json","X-Portfolio-Token":token},body:JSON.stringify(state.settings)});const result=await r.json();if(!r.ok)throw Error(result.error);clearDirty("Saved. Build Portfolio to update the website.")}catch(e){setStatus(e.message,"error")}}

el("addExistingImage").addEventListener("click",()=>{const path=el("galleryExisting").value;if(!path)return;state.gallery.push({kind:"existing",path});state.galleryChanged=true;renderGallery();markDirty()});
