const boardEl = document.querySelector("#board");
const statusEl = document.querySelector("#status");
const turnBadge = document.querySelector("#turnBadge");
const messageEl = document.querySelector("#message");
const logEl = document.querySelector("#log");
const hintSection = document.querySelector("#hintSection");
const hintsEl = document.querySelector("#hints");
const toggleHintsBtn = document.querySelector("#toggleHintsBtn");
const gameTypeEl = document.querySelector("#gameType");
const boardSizeEl = document.querySelector("#boardSize");

const labels = {
  B: "黑方",
  W: "白方",
  null: "平局",
};

async function api(action, data = {}) {
  const response = await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, ...data }),
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "操作失败");
  }
  render(result);
}

async function loadState() {
  const response = await fetch("/api/state");
  render(await response.json());
}

function render(state) {
  gameTypeEl.value = state.gameType;
  boardSizeEl.value = state.size;
  statusEl.textContent = `${state.displayName} · ${state.status}`;
  turnBadge.textContent = state.gameOver ? `结果：${labels[state.winner]}` : labels[state.currentPlayer];
  messageEl.textContent = state.message;
  renderHints(state);
  renderLog(state.messages || [state.message]);

  boardEl.style.gridTemplateColumns = `repeat(${state.size}, 1fr)`;
  boardEl.replaceChildren();
  const stars = starPoints(state.size);
  state.board.forEach((row, rowIndex) => {
    row.forEach((piece, colIndex) => {
      const cell = document.createElement("button");
      cell.className = "cell";
      cell.type = "button";
      cell.title = `${rowIndex + 1}, ${colIndex + 1}`;
      cell.addEventListener("click", () => api("move", { row: rowIndex + 1, col: colIndex + 1 }).catch(showError));
      if (piece === "." && stars.has(`${rowIndex},${colIndex}`)) {
        cell.classList.add("star");
      }
      if (piece !== ".") {
        const stone = document.createElement("span");
        stone.className = `stone ${piece === "B" ? "black" : "white"}`;
        cell.append(stone);
      }
      boardEl.append(cell);
    });
  });
}

function renderHints(state) {
  hintSection.classList.toggle("hidden", !state.hintsVisible);
  toggleHintsBtn.textContent = state.hintsVisible ? "隐藏" : "显示";
  const hints = [
    "点击棋盘交叉点落子，黑白双方自动轮换。",
    "悔棋会回退一步，棋局结束后仍可重新开始。",
    "导出存档会下载 JSON 文件，导入存档会覆盖当前局面。",
  ];
  if (state.gameType === "go") {
    hints.push("围棋支持提子、自杀手拦截、打劫重复局面拦截和虚着。");
  } else {
    hints.push("五子棋任一方向连成五子会自动判胜。");
  }
  hintsEl.replaceChildren(...hints.map((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    return item;
  }));
}

function renderLog(messages) {
  logEl.replaceChildren(...messages.slice().reverse().map((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    return item;
  }));
}

function starPoints(size) {
  const presets = {
    19: [3, 9, 15],
    15: [3, 7, 11],
    13: [3, 6, 9],
    9: [2, 4, 6],
  };
  const points = presets[size] || [];
  return new Set(points.flatMap((row) => points.map((col) => `${row},${col}`)));
}

function showError(error) {
  messageEl.textContent = `错误：${error.message}`;
}

document.querySelector("#startBtn").addEventListener("click", () => {
  api("start", {
    gameType: gameTypeEl.value,
    size: Number(boardSizeEl.value),
  }).catch(showError);
});

document.querySelector("#restartBtn").addEventListener("click", () => api("restart").catch(showError));
document.querySelector("#undoBtn").addEventListener("click", () => api("undo").catch(showError));
document.querySelector("#passBtn").addEventListener("click", () => api("pass").catch(showError));
document.querySelector("#resignBtn").addEventListener("click", () => api("resign").catch(showError));
toggleHintsBtn.addEventListener("click", () => api("toggleHints").catch(showError));

document.querySelector("#importFile").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) {
    return;
  }
  try {
    const data = JSON.parse(await file.text());
    await api("import", { data });
  } catch (error) {
    showError(error);
  } finally {
    event.target.value = "";
  }
});

loadState().catch(showError);
