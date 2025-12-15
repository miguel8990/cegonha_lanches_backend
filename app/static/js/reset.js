// site/js/reset.js

const isLocalhost =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

const API_BASE_URL = isLocalhost
  ? `http://${window.location.hostname}:5000/api`
  : "/api"; // <--- NOVO: Caminho relativo

function showToast(msg, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return alert(msg); // Fallback se não tiver container na pág reset
  const div = document.createElement("div");
  div.className = `toast ${type}`;
  div.innerHTML = `<span>${msg}</span>`;
  container.appendChild(div);
  setTimeout(() => div.remove(), 4000);
}

document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get("token");

  const stepRequest = document.getElementById("step-request");
  const stepNewPass = document.getElementById("step-new-pass");

  if (token) {
    stepRequest.classList.remove("active");
    stepNewPass.classList.add("active");
    initResetForm(token);
  } else {
    stepRequest.classList.add("active");
    initRequestForm();
  }
});

// MODO A: Pedir Link (Esqueci a senha)
function initRequestForm() {
  const form = document.getElementById("form-request-reset");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("email-request").value;
    const btn = form.querySelector("button");
    btn.innerText = "Enviando...";
    btn.disabled = true;

    try {
      const res = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
        // Não precisa de credentials aqui, rota pública
      });
      // Sempre diz sucesso por segurança
      document.getElementById("step-request").classList.remove("active");
      document.getElementById("step-sent").classList.add("active");
    } catch (error) {
      showToast("Erro de conexão.", "error");
      btn.innerText = "Tentar Novamente";
      btn.disabled = false;
    }
  });
}

// MODO B: Salvar Nova Senha (Tenho token do email)
function initResetForm(token) {
  const form = document.getElementById("form-confirm-reset");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const p1 = document.getElementById("new-password").value;
    const p2 = document.getElementById("confirm-password").value;
    const btn = form.querySelector("button");

    if (p1 !== p2) return showToast("As senhas não conferem!", "warning");
    if (p1.length < 8) return showToast("Senha muito curta.", "warning");

    btn.innerText = "Salvando...";
    btn.disabled = true;

    try {
      // 🔥 AQUI: Enviamos o token via HEADER Authorization
      // Pois o usuário ainda não logou, então não tem cookie de sessão.
      // O backend está configurado para aceitar ['cookies', 'headers']
      const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ new_password: p1 }),
      });

      const data = await res.json();

      if (res.ok) {
        alert("Sucesso! Sua senha foi alterada. Faça login agora.");
        window.location.href = "index.html";
      } else {
        showToast(data.error || "Link expirado ou inválido.", "error");
        btn.innerText = "Erro";
      }
    } catch (error) {
      showToast("Erro ao conectar.", "error");
      btn.disabled = false;
    }
  });
}
