let board = null;
let socket = null;

let username = "";
let roomCode = "";
let playerColor = "";
let backendUrl = "";
let wsUrl = "";
let selectedSquare = null;

function getBackendUrls() {
    backendUrl = window.location.origin;
    wsUrl = window.location.origin.replace("http", "ws");
}

function log(message, type = "info") {
    const logs = document.getElementById("logs");

    if (!logs) return;

    logs.innerHTML += `<div class="log-item ${type}">${message}</div>`;
    logs.scrollTop = logs.scrollHeight;
}

function clearHighlights() {
    $("#board .square-55d63").removeClass("highlight-square");
}

function highlightSquare(square) {
    clearHighlights();
    $(`#board .square-${square}`).addClass("highlight-square");
}

function initBoard() {
    board = Chessboard("board", {
        draggable: false,
        position: "start",
        pieceTheme: "https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png"
    });

    $("#board").on("click", ".square-55d63", function () {
        const classes = $(this).attr("class").split(" ");
        let clickedSquare = null;

        for (let cls of classes) {
            if (cls.startsWith("square-") && cls !== "square-55d63") {
                clickedSquare = cls.replace("square-", "");
                break;
            }
        }

        handleSquareClick(clickedSquare);
    });
}

async function handleSquareClick(square) {
    if (!roomCode || !username) {
        alert("Create or join room first");
        return;
    }

    if (!selectedSquare) {
        selectedSquare = square;
        highlightSquare(square);
        log(`Selected ${square}`, "info");
        return;
    }

    const move = selectedSquare + square;
    clearHighlights();

    const success = await sendMove(move);

    if (success) {
        log(`Move sent: ${move}`, "success");
    }

    selectedSquare = null;
}

async function createUser() {
    getBackendUrls();

    username = document.getElementById("username").value.trim();

    if (!username) {
        alert("Enter player name");
        return;
    }

    try {
        const res = await fetch(`${backendUrl}/api/users`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username})
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail);
            return;
        }

        log(data.message, "success");

    } catch (error) {
        log("Backend not connected", "error");
    }
}

async function createRoom() {
    getBackendUrls();

    username = document.getElementById("username").value.trim();

    if (!username) {
        alert("Enter player name");
        return;
    }

    try {
        const res = await fetch(`${backendUrl}/api/rooms/create`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username})
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail);
            log(data.detail, "error");
            return;
        }

        roomCode = data.room_code;
        playerColor = data.player_color;

        document.getElementById("roomText").innerText = roomCode;
        document.getElementById("colorText").innerText = playerColor;
        document.getElementById("statusText").innerText = "Waiting for opponent";
        document.getElementById("turnText").innerText = "White";

        board.position(data.fen);
        board.orientation(playerColor);

        connectSocket();

        log(`Room created successfully: ${roomCode}`, "success");
        log("Share this room code with the second player.", "info");

    } catch (error) {
        log("Create room failed. Check backend/database.", "error");
    }
}

async function joinRoom() {
    getBackendUrls();

    username = document.getElementById("username").value.trim();
    roomCode = document.getElementById("roomInput").value.trim().toUpperCase();

    if (!username || !roomCode) {
        alert("Enter player name and room code");
        return;
    }

    try {
        const res = await fetch(`${backendUrl}/api/rooms/join`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                username,
                room_code: roomCode
            })
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail);
            log(data.detail, "error");
            return;
        }

        playerColor = data.player_color;

        document.getElementById("roomText").innerText = roomCode;
        document.getElementById("colorText").innerText = playerColor;
        document.getElementById("statusText").innerText = data.status;
        document.getElementById("turnText").innerText = "White";

        board.position(data.fen);
        board.orientation(playerColor);

        connectSocket();

        log(`Joined room successfully: ${roomCode}`, "success");

    } catch (error) {
        log("Join room failed. Check backend connection.", "error");
    }
}

function connectSocket() {
    if (socket) {
        socket.close();
    }

    socket = new WebSocket(`${wsUrl}/ws/${roomCode}`);

    socket.onopen = () => {
        log("Connected to distributed WebSocket server", "success");
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "player_joined") {
            document.getElementById("statusText").innerText = data.status;
            log(data.message, "success");
        }

        if (data.type === "move") {
            board.position(data.fen);

            document.getElementById("turnText").innerText =
                data.turn.charAt(0).toUpperCase() + data.turn.slice(1);

            document.getElementById("statusText").innerText = data.status;

            log(`${data.player} moved ${data.move}`, "info");

            if (data.check) {
                log("Check!", "error");
            }

            if (data.checkmate) {
                log(`Checkmate! Winner: ${data.winner}`, "success");
                document.getElementById("statusText").innerText =
                    `Winner: ${data.winner}`;
            }

            if (data.stalemate) {
                log("Game draw by stalemate", "info");
            }
        }
    };

    socket.onclose = () => {
        log("Disconnected from server", "error");
    };
}

async function sendMove(move) {
    try {
        const res = await fetch(`${backendUrl}/api/move`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                username,
                room_code: roomCode,
                move
            })
        });

        const data = await res.json();

        if (!res.ok) {
            log(data.detail, "error");
            return false;
        }

        return true;

    } catch (error) {
        log("Move failed. Server error.", "error");
        return false;
    }
}

async function shareRoomCode() {
    if (!roomCode) {
        alert("Create a room first");
        return;
    }

    const text =
        `Join my Distributed Chess Game!\n\n` +
        `Game Link: ${window.location.origin}\n` +
        `Room Code: ${roomCode}\n\n` +
        `Open the link, enter your name, paste the room code, and join.`;

    try {
        if (navigator.share) {
            await navigator.share({
                title: "Distributed Chess Game",
                text: text
            });
        } else {
            await navigator.clipboard.writeText(text);
            alert("Room code and link copied!");
        }

        log("Room code shared successfully", "success");

    } catch (error) {
        log("Share cancelled or failed", "error");
    }
}

window.onload = initBoard;