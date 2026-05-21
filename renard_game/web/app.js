const boardEl = document.querySelector("#board");
const statusEl = document.querySelector("#status");
const turnBadge = document.querySelector("#turnBadge");
const messageEl = document.querySelector("#message");
const gameTypeEl = document.querySelector("#gameType");
const defaultBoardSize = 15;

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
  statusEl.textContent = `${state.displayName} · ${state.status}`;
  turnBadge.textContent = state.gameOver ? `结果：${labels[state.winner]}` : labels[state.currentPlayer];
  messageEl.textContent = state.message;

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
    size: defaultBoardSize,
  }).catch(showError);
});

document.querySelector("#restartBtn").addEventListener("click", () => api("restart").catch(showError));
document.querySelector("#undoBtn").addEventListener("click", () => api("undo").catch(showError));
document.querySelector("#passBtn").addEventListener("click", () => api("pass").catch(showError));
document.querySelector("#resignBtn").addEventListener("click", () => api("resign").catch(showError));

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
