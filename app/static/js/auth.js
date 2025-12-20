// site/js/auth.js
import { loginUser, API_BASE_URL, fetchCurrentUser } from "./api.js";
import { openAuthModal } from "./main.js";
import { showToast } from "./utils.js";
// ==========================================
//  GESTÃO DE SESSÃO (Interface Visual)
//  Nota: O Token real fica num Cookie HttpOnly invisível ao JS.
// ==========================================
let currentUserInMemory = null;

export function saveSession(token_ignored, user) {
  // 1. Salva dados completos na MEMÓRIA RAM (para uso imediato do socket/api)
  currentUserInMemory = user;

  // 2. Prepara objeto "Leve" apenas para controle de UI (Botões)
  const sessionUI = {
    is_logged: true,
    ui_name: user.name.split(" ")[0], // Só o primeiro nome
    role: user.role, // Para mostrar botão Admin
  };

  // 3. Salva no disco apenas o sinalizador visual
  localStorage.setItem("session_ui", JSON.stringify(sessionUI));

  // 4. LIMPEZA DE LEGADO: Remove dados antigos inseguros se existirem
  localStorage.removeItem("user");
  localStorage.removeItem("access_token");
}

export async function verifySession() {
  // 1. Chama o endpoint /auth/me (o navegador envia o cookie automaticamente)
  const user = await fetchCurrentUser();

  if (user) {
    // SUCESSO: Backend confirmou o cookie.
    // Atualizamos a memória e o localStorage visual.
    // Isso conserta o problema: Se deletar localStorage, essa função recria ele.
    saveSession(null, user);
    console.log("✅ Sessão validada via Cookie HttpOnly");
  } else {
    // FALHA: Cookie expirou ou é inválido.
    // Forçamos logout visual.
    console.warn("🔒 Sessão inválida. Limpando UI.");
    clearSession();
  }

  // Atualiza a tela (esconde botão login, mostra perfil)
  if (window.checkLoginState) window.checkLoginState();
}

export function getSession() {
  // Tenta ler o dado visual
  const uiStr = localStorage.getItem("session_ui");
  let uiData = null;
  try {
    uiData = uiStr ? JSON.parse(uiStr) : null;
  } catch (e) {
    clearSession();
  }

  // Se tivermos dados em memória (pós-load), eles têm prioridade
  if (currentUserInMemory) {
    return {
      logged: true,
      user: currentUserInMemory, // Retorna objeto completo se estiver na RAM
    };
  }

  // Se só tivermos o dado visual (ex: acabou de dar F5), retornamos o básico
  if (uiData && uiData.is_logged) {
    return {
      logged: true,
      user: { name: uiData.ui_name, role: uiData.role }, // Mock para UI funcionar
    };
  }

  return { logged: false, user: {} };
}
export function getCurrentUserSecure() {
  return currentUserInMemory;
}
export function clearSession() {
  localStorage.removeItem("session_ui"); // Remove sinalizador visual
  localStorage.removeItem("user"); // Garante limpeza de legado
  currentUserInMemory = null; // Limpa memória
}

export async function logout() {
  try {
    // Avisa backend para matar o cookie
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch (e) {
    console.error("Erro logout:", e);
  }

  clearSession();
  if (window.showToast) window.showToast("Sessão terminada.", "info");

  // Atualiza UI imediatamente sem reload forçado (UX melhor)
  if (window.checkLoginState) window.checkLoginState();
  setTimeout(() => (window.location.href = "index.html"), 500);
}

// Mantido para compatibilidade, mas retorna null (segurança)
export function getToken() {
  return null;
}

// ==========================================
//  LÓGICA DE PÁGINAS (Magic Link & Login)
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  // Apenas configura; a execução real é no main.js para evitar corrida
});

// ... (código anterior)

export async function checkMagicLinkReturn() {
  const params = new URLSearchParams(window.location.search);
  const status = params.get("status");

  if (status === "verified") {
    if (window.showToast) window.showToast("Validando acesso...", "info");

    // 1. Espera crítica para o navegador processar o Set-Cookie
    await new Promise((resolve) => setTimeout(resolve, 500)); // Aumentei para 500ms por segurança

    // 2. Tenta ler a sessão usando o cookie que DEVERIA estar lá
    const user = await fetchCurrentUser();

    if (user) {
      // SUCESSO: O cookie passou!
      saveSession(null, user);
      if (window.showToast)
        window.showToast(`Bem-vindo, ${user.name}!`, "success");

      // Limpa a URL
      window.history.replaceState({}, document.title, window.location.pathname);
      if (window.checkLoginState) window.checkLoginState();
    } else {
      // 🚨 ERRO CRÍTICO DETECTADO 🚨
      // A URL diz que logou, mas o Backend diz que não tem cookie.
      console.error("ERRO: Cookie de terceiros bloqueado pelo navegador.");

      // Limpa visualmente e mostra o modal de ajuda
      clearSession();
      if (window.showCookieError) {
        window.showCookieError();
      } else {
        alert("Seu navegador bloqueou o login. Habilite cookies de terceiros.");
      }
    }
  } else if (status === "error_token") {
    if (window.showToast)
      window.showToast("Link inválido ou expirado.", "error");
    window.history.replaceState({}, document.title, window.location.pathname);
  }
}

// Formulário da página login.html (Standalone)
const form = document.getElementById("standalone-login-form");
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("page-email").value;
    const pass = document.getElementById("page-password").value;
    const btn = form.querySelector("button");
    const txt = btn.innerText;

    btn.innerText = "Verificando...";
    btn.disabled = true;

    // loginUser (do api.js) já deve estar usando fetchAuth ou credentials: 'include'
    const res = await loginUser(email, pass);

    if (res.success) {
      saveSession(null, res.user);
      window.location.href = "index.html";
    } else {
      showToast("Erro: " + res.error);
      btn.innerText = txt;
      btn.disabled = false;
    }
  });
}

// Funções para abrir/fechar modal (Helpers globais)
export function abrirModalLogin(mensagemOpcional) {
  const modal = document.getElementById("modal-auth");
  if (modal) {
    modal.style.display = "flex";
    if (window.switchAuthTab) window.switchAuthTab("acesso"); // Abre na aba inicial
    if (mensagemOpcional && window.showToast)
      window.showToast(mensagemOpcional, "info");
  }
}

export function fecharModalLogin() {
  const modal = document.getElementById("modal-auth"); // Ajustado ID padrão
  if (modal) modal.style.display = "none";
}

// ==========================================
//  MAGIC LINK (Acesso sem senha)
// ==========================================

export async function pedirMagicLink(event) {
  event.preventDefault();
  const email = document.getElementById("magic-email").value;
  const btn = event.target.querySelector("button");
  const txtOriginal = btn.innerText;

  btn.innerText = "Enviando...";
  btn.disabled = true;

  try {
    // [CORREÇÃO] Usando a constante importada para evitar duplicação de lógica
    const res = await fetch(`${API_BASE_URL}/auth/magic-login/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
      credentials: "include", // Boa prática para manter consistência CORS
    });

    const data = await res.json();

    if (res.ok) {
      if (window.abrirModalMagic) {
        window.abrirModalMagic();
      } else {
        showToast("Verifique seu e-mail! Link enviado.", "success");
      }
      const emailInput = document.getElementById("login-email");
      if (emailInput) emailInput.value = "";
    } else {
      showToast(data.error || "Erro ao enviar link.", "error");
      // Se o erro for de nome, muda aba (lógica específica do seu app)
      if (data.error && data.error.includes("Nome")) {
        if (window.switchAuthTab) window.switchAuthTab("register");
      }
    }
  } catch (error) {
    console.error(error);
    showToast("Erro de conexão com o servidor.", "error");
  } finally {
    btn.innerText = txtOriginal;
    btn.disabled = false;
  }
}

// ==========================================
//  GOOGLE AUTH
// ==========================================

async function handleGoogleCredentialResponse(response) {
  console.log("Token Google recebido...");

  try {
    const res = await fetch(`${API_BASE_URL}/auth/google`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ credential: response.credential }),
      credentials: "include", // Garante que o navegador aceite o Set-Cookie
    });

    const data = await res.json();

    if (res.ok) {
      // 1. Força uma pequena espera para o navegador processar o cookie
      await new Promise((resolve) => setTimeout(resolve, 100));

      const checkUser = await fetchCurrentUser();
      if (!checkUser) {
        showCookieError(); // Cookie Google também foi bloqueado
        return;
      }

      // 2. Salva a sessão visualmente AGORA (sem depender do reload/cookie imediato)
      // Isso garante que a UI mostre "Olá, Nome" instantaneamente
      saveSession(null, data.user);

      if (window.showToast)
        window.showToast(`Bem-vindo, ${data.user.name}!`, "success");

      // 3. Atualiza a tela atual (botões de login somem, perfil aparece)
      if (window.checkLoginState) window.checkLoginState();

      // 4. Só recarrega a página depois de um tempo seguro (1.5s)
      // Isso dá tempo de sobra para o cookie persistir no disco/memória do navegador
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } else {
      alert(data.message || "Erro ao logar com Google");
    }
  } catch (error) {
    console.error("Erro comunicação API:", error);
    alert("Erro ao conectar com o servidor.");
  }
}

export function initGoogleButton() {
  let tentativas = 0;
  const intervalo = setInterval(() => {
    if (window.google) {
      clearInterval(intervalo);

      // Lembre-se de substituir pelo seu Client ID real se mudar
      window.google.accounts.id.initialize({
        client_id:
          "681186932916-jsjkbpajai5mchsbrfrbmfshh27cqpo6.apps.googleusercontent.com",
        callback: handleGoogleCredentialResponse,
      });

      const btnContainer = document.getElementById("google-btn-container");
      if (btnContainer) {
        window.google.accounts.id.renderButton(btnContainer, {
          theme: "outline",
          size: "large",
          type: "standard",
          text: "signin_with",
        });
      }
    } else {
      tentativas++;
      if (tentativas > 20) {
        // 10 segundos
        clearInterval(intervalo);
        console.warn("Google Auth script não carregou.");
      }
    }
  }, 500);
}
