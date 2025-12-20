import {
  fetchMenu,
  fetchCombos,
  submitOrder,
  loginUser,
  registerUser,
  updateUserProfile,
  fetchAddresses,
  addAddress,
  setActiveAddress,
  deleteAddress,
  fetchMyOrders,
  getChatMessages,
  sendChatMessage,
  fetchPublicCoupons,
  fetchNeighborhoodsPublic,
  fetchSchedule,
  fetchBebidas,
} from "./api.js";
import {
  checkMagicLinkReturn,
  abrirModalLogin,
  getSession,
  saveSession,
  clearSession,
  pedirMagicLink,
  initGoogleButton,
  logout as authLogout,
  verifySession,
  getCurrentUserSecure,
} from "./auth.js";

import { showToast } from "./utils.js";

// Estado Global
let carrinho = [];
let menuGlobal = [];
let produtoSelecionado = null; //
let itemEmPersonalizacao = null;
let cuponsDisponiveis = [];
let cupomSelecionado = null; // Objeto do cupom
let taxaEntregaAtual = 0;
let lojaAberta = false;
let horariosGlobal = [];
let reviewsCarregadas = [];

// 2. Garante que ela também exista no window (para compatibilidade com HTML e códigos antigos)

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Verifica se tem retorno de Magic Link (aguarda a checagem)
  // Se o usuário veio do email, essa função faz o login E a verificação de sessão.
  await checkMagicLinkReturn();

  // 2. Verifica o estado da sessão global
  // Esta função é o fallback para todas as outras recargas de página.
  // Ela deve ser executada após o checkMagicLinkReturn para não causar problemas de ordem.
  await verifySession();

  initMenu();
  initCombos();
  initBebidas();
  carregarCarrinhoLocal();
  initContactForm();
  initMobileMenu();
  initScrollEffects();
  initHorarioFuncionamento();
  initBairrosSelect();
  salvarCarrinhoLocal();
  checkMagicLinkReturn();
  initGoogleButton();
  verificarUsuarioLogado();
  carregarAvaliacoes();
  iniciarSistemaEstrelas();
  initCookieConsent();

  // Verifica Login ao carregar
  checkLoginState();
  initAuthModalLogic();
  initCoupons();

  // Fecha modais ao clicar fora
  // Fecha modais e menus ao clicar fora
  window.onclick = (event) => {
    const modalProd = document.getElementById("modal-personalizacao");
    const modalAuth = document.getElementById("modal-auth");
    const accPhone = document.getElementById("acc-whatsapp");
    const modalOrders = document.getElementById("modal-orders");
    const profileMenu = document.getElementById("profile-menu");
    const profileIcon = document.querySelector(".profile-icon");

    // 1. Fecha Modais Grandes (se clicar no fundo escuro)
    if (event.target === modalProd) fecharModal();
    if (event.target === modalAuth) closeAuthModal();
    if (event.target === modalOrders) fecharModalPedidos();
    if (accPhone) {
      accPhone.addEventListener("input", (e) => {
        let v = e.target.value.replace(/\D/g, "");
        if (v.length > 11) v = v.slice(0, 11);
        if (v.length > 2) v = `(${v.substring(0, 2)}) ${v.substring(2)}`;
        if (v.length > 7) v = `${v.substring(0, 10)}-${v.substring(10)}`;
        e.target.value = v;
      });
    }

    // 2. Fecha o Menu de Perfil (Dropdown)

    // Se o menu existe e está aberto...
    if (profileMenu && profileMenu.style.display === "block") {
      // ...e o clique NÃO foi dentro do menu E NÃO foi no ícone que abre ele
      if (
        !profileMenu.contains(event.target) &&
        !profileIcon.contains(event.target)
      ) {
        profileMenu.style.display = "none";
      }
    }
  };

  // ===========================================================================
  //  SISTEMA REAL-TIME (SOCKET.IO) - CLIENTE
  // ===========================================================================

  // 1. Conexão
  const socketUrl =
    window.location.hostname === "localhost"
      ? "http://localhost:5000"
      : "https://cegonha-lanches-backend.onrender.com";
  const socket = io(socketUrl);

  socket.on("connect", () => {
    if (typeof io !== "undefined") {
      // 1. Conexão
      const socketUrl =
        window.location.hostname === "localhost"
          ? "http://localhost:5000"
          : "https://cegonha-lanches-backend.onrender.com";
      const socket = io(socketUrl);

      socket.on("connect", () => {
        console.log("🟢 Conectado ao servidor!");
      });

      // ... (resto do código do socket.on 'status_update', 'chat_message', etc) ...
      // Mantenha todo o resto do código do socket DENTRO deste bloco if
    } else {
      console.warn(
        "Socket.IO não carregado nesta página. Chat e notificações desativados."
      );
    }
  });

  // 2. Atualização de Status do Pedido
  socket.on("status_update", (data) => {
    const { user } = getSession();
    // Só reage se o pedido for MEU
    if (user && user.id === data.user_id) {
      console.log("🔔 Seu pedido mudou de status:", data.status);

      // Toca som de notificação suave
      const audio = new Audio("assets/notification.mp3");
      audio.play().catch(() => {});

      showToast(
        `Seu pedido #${data.order_id} agora está: ${data.status}`,
        "success"
      );

      // Se o modal de pedidos estiver aberto, atualiza a lista
      const modalOrders = document.getElementById("modal-orders");
      if (modalOrders && modalOrders.style.display === "flex") {
        abrirHistoricoPedidos(); // Recarrega a lista
      }
    }
  });

  // 3. Chat Instantâneo
  socket.on("chat_message", (msg) => {
    const { user } = getSession();

    // Só mostra se for mensagem da minha conversa
    if (user && user.id === msg.user_id) {
      const chatWidget = document.getElementById("chat-widget");

      // Se o chat estiver aberto (não tiver a classe 'minimized')
      if (chatWidget && !chatWidget.classList.contains("minimized")) {
        // Adiciona a mensagem na tela sem recarregar tudo
        adicionarMensagemNaTela(msg);
      } else if (msg.is_from_admin) {
        // Se fechado, notifica
        showToast("Nova mensagem do restaurante!", "info");
        const icon = document.getElementById("chat-icon");
        if (icon) icon.style.color = "var(--color-gold)"; // Feedback visual simples
      }
    }
  });

  // 4. Controle de Estoque (Pausar/Despausar)
  socket.on("product_toggle", (data) => {
    console.log("📦 Atualização de estoque:", data);

    // Procura o botão de compra desse produto na tela
    const btn = document.querySelector(
      `button[onclick="adicionarAoCarrinho(${data.id})"]`
    );
    const card = btn ? btn.closest(".product-card") : null;

    if (btn && card) {
      if (!data.is_available) {
        // Produto Esgotou
        btn.disabled = true;
        btn.innerText = "Indisponível";
        btn.style.backgroundColor = "#555";
        card.style.opacity = "0.7";
      } else {
        // Produto Voltou
        btn.disabled = false;
        btn.innerHTML = `Adicionar <i class="fa-solid fa-cart-plus"></i>`;
        btn.style.backgroundColor = ""; // Volta ao original (CSS)
        card.style.opacity = "1";
      }
    }
  });
});

// EXPORTA FUNÇÕES PARA O HTML USAR (onclick="")
window.adicionarAoCarrinho = adicionarAoCarrinho;
window.toggleCart = toggleCart;
window.removerItem = removerItem;
window.finalizarPedido = finalizarPedido;
window.alterarQuantidade = alterarQuantidade;

window.alterarQuantidadeCarrinho = alterarQuantidadeCarrinho;

window.fecharModal = fecharModal;
window.adicionarItemDoModal = adicionarItemDoModal;
window.atualizarSelecaoModal = atualizarSelecaoModal;
window.mudarQtdModal = mudarQtdModal;
// Auth Exports
window.openAuthModal = openAuthModal;
window.closeAuthModal = closeAuthModal;
window.switchAuthTab = switchAuthTab;
window.toggleProfileMenu = toggleProfileMenu;

window.fecharModalAuth = closeAuthModal;
window.openAccountModal = openAccountModal;
window.closeAccountModal = closeAccountModal;
window.saveAccountDetails = saveAccountDetails;
window.toggleMobileMenu = toggleMobileMenu;
window.openAddressesModal = openAddressesModal;
window.closeAddressesModal = closeAddressesModal;
window.toggleAddAddressForm = toggleAddAddressForm;
window.selecionarEnderecoAtivo = selecionarEnderecoAtivo;
window.excluirEndereco = excluirEndereco;
window.abrirHistoricoPedidos = abrirHistoricoPedidos;
window.fecharModalPedidos = fecharModalPedidos;
window.mostrarForcaSenha = mostrarForcaSenha;
window.toggleChat = toggleChat;
window.enviarMensagemChat = enviarMensagemChat;
window.handleChatKey = handleChatKey;
window.toggleTroco = toggleTroco;

// --- 1. AUTENTICAÇÃO ---

// 1. Atualize a função checkLoginState
function checkLoginState() {
  // Pega dados da sessão (pode vir do LS ou da Memória)
  const { logged, user } = getSession();

  const btnLogin = document.getElementById("btn-open-login");
  const profileArea = document.getElementById("user-profile-area");
  const nameDisplay = document.getElementById("user-name-display");
  const adminLink = document.getElementById("admin-link");

  // Preenchimento de formulários (Checkout/Perfil)
  // Só preenche se tivermos os dados REAIS em memória (pós-load do verifySession)
  const realUser = getCurrentUserSecure();
  if (realUser) {
    if (document.getElementById("name"))
      document.getElementById("name").value = realUser.name || "";
    if (document.getElementById("phone"))
      document.getElementById("phone").value = realUser.whatsapp || "";
  }

  if (logged) {
    // Logado
    if (btnLogin) btnLogin.style.display = "none";
    if (profileArea) profileArea.style.display = "flex";

    // Nome vem do LocalStorage "light" ou da memória
    if (nameDisplay && user.name) {
      nameDisplay.innerText = `Olá, ${user.name.split(" ")[0]}`;
    }

    if (adminLink) {
      adminLink.style.display =
        user.role === "admin" || user.role === "super_admin" ? "block" : "none";
    }

    verificarUsuarioLogado(); // Atualiza UI de avaliações
  } else {
    // Deslogado
    if (btnLogin) btnLogin.style.display = "flex";
    if (profileArea) profileArea.style.display = "none";
    if (adminLink) adminLink.style.display = "none";
  }
}

export function openAuthModal() {
  document.getElementById("modal-auth").style.display = "flex";
  switchAuthTab("acesso");
}

function closeAuthModal() {
  document.getElementById("modal-auth").style.display = "none";

  // 1. Limpa os dados digitados
  const loginForm = document.getElementById("form-login");
  const regForm = document.getElementById("form-register");
  if (loginForm) loginForm.reset();
  if (regForm) regForm.reset();

  // 2. (Opcional) Reseta visualmente para a aba de Login
  // Assim, se o usuário abrir de novo, começa do início
  switchAuthTab("login");

  // 3. (Opcional) Restaura o texto dos botões se estiverem como "Enviando..."
  if (loginForm) {
    const btn = loginForm.querySelector("button");
    if (btn) {
      btn.innerText = "Entrar";
      btn.disabled = false;
    }
  }
  if (regForm) {
    const btn = regForm.querySelector("button");
    if (btn) {
      btn.innerText = "Cadastrar";
      btn.disabled = false;
    }
  }
}

// site/js/main.js

function switchAuthTab(tab) {
  // 1. Pega os formulários
  const magicForm = document.getElementById("form-magic-login");
  const passForm = document.getElementById("form-password-login");
  const regForm = document.getElementById("form-register");

  // 2. Pega os botões das abas
  const btns = document.querySelectorAll(".auth-tabs .tab-btn");

  // 3. Reseta tudo (esconde forms e remove classe active)
  magicForm.style.display = "none";
  passForm.style.display = "none";
  regForm.style.display = "none";
  btns.forEach((btn) => btn.classList.remove("active"));

  // 4. Ativa a aba correta
  if (tab === "acesso") {
    magicForm.style.display = "block";
    if (btns[0]) btns[0].classList.add("active");
  } else if (tab === "login") {
    passForm.style.display = "block";
    if (btns[1]) btns[1].classList.add("active");
  } else if (tab === "register") {
    regForm.style.display = "block";
    if (btns[2]) btns[2].classList.add("active");
  }
}

// Não esqueça de garantir que ela está disponível globalmente:
window.switchAuthTab = switchAuthTab;

function initAuthModalLogic() {
  // 1. Magic Link Submit
  const magicForm = document.getElementById("form-magic-login");
  if (magicForm) {
    magicForm.addEventListener("submit", pedirMagicLink);
  }

  // 2. [NOVO] Password Login Submit
  const passForm = document.getElementById("form-password-login");
  if (passForm) {
    passForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const email = document.getElementById("login-email").value;
      const password = document.getElementById("login-password").value;
      const btn = passForm.querySelector("button");
      const originalText = btn.innerText;

      btn.innerText = "Entrando...";
      btn.disabled = true;

      // Chama a função de login da API (já existente)
      const res = await loginUser(email, password);

      if (res.success) {
        // Salva sessão (Cookies) e atualiza a tela
        saveSession(res.token, res.user);
        checkLoginState();
        closeAuthModal();
        showToast(
          `Bem-vindo de volta, ${res.user.name.split(" ")[0]}!`,
          "success"
        );
      } else {
        showToast(res.error || "Email ou senha incorretos.", "error");
      }

      btn.innerText = originalText;
      btn.disabled = false;
    });
  }

  // Register Submit
  const regForm = document.getElementById("form-register");
  if (regForm) {
    // [NOVO] MÁSCARA PARA O WHATSAPP NO CADASTRO
    const whatsappInput = regForm.querySelector('input[name="whatsapp"]');
    if (whatsappInput) {
      whatsappInput.addEventListener("input", (e) => {
        let v = e.target.value.replace(/\D/g, ""); // Remove tudo que não é dígito
        if (v.length > 11) v = v.slice(0, 11); // Limita a 11 números

        // Aplica a máscara (XX) XXXXX-XXXX
        if (v.length > 2) v = `(${v.substring(0, 2)}) ${v.substring(2)}`;
        if (v.length > 7) v = `${v.substring(0, 10)}-${v.substring(10)}`;

        e.target.value = v;
      });
    }

    regForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      // Captura os dados
      const data = {
        name: regForm.querySelector('input[name="name"]').value,
        email: regForm.querySelector('input[name="email"]').value,
        password: regForm.querySelector('input[name="password"]').value,
        // Remove a máscara antes de enviar pro banco (opcional, mas recomendado)
        whatsapp: regForm.querySelector('input[name="whatsapp"]').value || "",
      };

      const btn = regForm.querySelector("button");
      const txt = btn.innerText;
      btn.innerText = "Criando...";
      btn.disabled = true;

      const res = await registerUser(data);

      if (res.success) {
        showToast(
          "Cadastro criado! Um link de confirmação foi enviado para seu email."
        );

        regForm.reset();
      } else {
        showToast(res.error);
      }
      btn.innerText = txt;
      btn.disabled = false;
    });
  }
}

function toggleProfileMenu() {
  const menu = document.getElementById("profile-menu");
  if (menu.style.display === "block") {
    menu.style.display = "none";
  } else {
    menu.style.display = "block";
  }
}

// Função ligada ao botão "Sair" do menu
window.logout = function () {
  // 1. Fecha o menu dropdown visualmente
  toggleProfileMenu();

  // 2. Atualiza a tela imediatamente para parecer que saiu (UX rápida)
  // (Opcional, pois o authLogout vai redirecionar a página em 1s)
  clearSession();
  checkLoginState();

  // 3. Chama a lógica real (API + Limpeza Profunda + Redirect)
  // Nota: Não precisa de 'await' aqui se não for fazer nada depois
  authLogout();
};

// --- 2. LÓGICA DO CARRINHO ---

function adicionarAoCarrinho(nome, preco, dadosExtras = {}) {
  const itemExistente = carrinho.find((item) => item.nome === nome);
  if (itemExistente) {
    itemExistente.quantity += 1;
  } else {
    carrinho.push({ nome, preco, quantity: 1, ...dadosExtras });
  }
  atualizarCarrinhoUI();
  atualizarBotoesMenu();
  animarCarrinho();
  showToast(`${nome} adicionado!`, "success");
  salvarCarrinhoLocal();
}

function removerItem(index) {
  carrinho.splice(index, 1);
  atualizarCarrinhoUI();
  atualizarBotoesMenu();
  showToast(`${nome} removido!`, "success");
  salvarCarrinhoLocal();
}

function atualizarCarrinhoUI() {
  const container = document.getElementById("cart-items");
  const contador = document.getElementById("cart-count");
  const totalSpan = document.getElementById("cart-total-price");
  if (!container) return;

  container.innerHTML = "";
  let total = 0;
  let totalItens = 0;

  if (carrinho.length === 0) {
    container.innerHTML = '<p class="empty-msg">Seu carrinho está vazio 🍔</p>';
    // [CORREÇÃO 1] Se vazio, remove cupom sem dar grito de erro
    if (cupomSelecionado) {
      cupomSelecionado = null;
      atualizarVisualDesconto();
    }
  } else {
    // ... (código de renderização dos itens continua igual) ...
    carrinho.forEach((item) => {
      total += item.preco * item.quantity;
      totalItens += item.quantity;
      const itemDiv = document.createElement("div");
      itemDiv.classList.add("cart-item-row");
      itemDiv.innerHTML = `
        <div style="flex: 1;">
            <h4 style="color:white; margin:0;">${item.nome}</h4>
            <small style="color:#aaa;">R$ ${(item.preco * item.quantity)
              .toFixed(2)
              .replace(".", ",")}</small>
        </div>
        <div class="cart-qty-controls">
            <button onclick="alterarQuantidadeCarrinho('${
              item.nome
            }', -1)">-</button>
            <span>${item.quantity}</span>
            <button onclick="alterarQuantidadeCarrinho('${
              item.nome
            }', 1)">+</button>
        </div>`;
      container.appendChild(itemDiv);
    });
  }

  if (contador) contador.innerText = totalItens;
  if (totalSpan)
    totalSpan.innerText = `R$ ${total.toFixed(2).replace(".", ",")}`;

  renderizarCupons();

  // [CORREÇÃO 2] Validação do Cupom Blindada
  const novoTotal = carrinho.reduce(
    (acc, item) => acc + item.preco * item.quantity,
    0
  );

  if (cupomSelecionado && novoTotal < cupomSelecionado.min_purchase) {
    cupomSelecionado = null;
    atualizarVisualDesconto();

    // O SEGREDO: Só mostra o aviso se o carrinho NÃO estiver vazio.
    // Se estiver vazio (novoTotal === 0), é limpeza pós-compra, então fica quieto.
    if (novoTotal > 0) {
      showToast("Cupom removido: Valor mínimo não atingido.", "warning");
    }
  } else if (cupomSelecionado) {
    atualizarVisualDesconto();
  }
}

function toggleCart(forceOpen = false) {
  const sidebar = document.getElementById("cart-sidebar");
  const overlay = document.getElementById("cart-overlay");

  if (forceOpen || !sidebar.classList.contains("open")) {
    sidebar.classList.add("open");
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
  } else {
    sidebar.classList.remove("open");
    overlay.classList.remove("open");
    document.body.style.overflow = "";
  }
}

function finalizarPedido() {
  if (carrinho.length === 0)
    return showToast("Adicione itens antes de fechar o pedido!", "warning");
  toggleCart();
  document.getElementById("contact").scrollIntoView({ behavior: "smooth" });
}

// --- 3. MENU E API ---

async function initMenu() {
  const menuGrid = document.getElementById("menu-grid");
  if (!menuGrid) return;
  try {
    const itens = await fetchMenu();
    menuGlobal = itens;
    menuGrid.innerHTML = itens.map(createMenuItemCard).join("");
    atualizarBotoesMenu();
  } catch (e) {
    menuGrid.innerHTML = "<p>Erro ao carregar cardápio</p>";
  }
}

async function initCombos() {
  const container = document.querySelector("#combos .carousel");
  if (!container) return;
  try {
    const itens = await fetchCombos();
    // Adiciona combos ao menu global para busca por ID
    itens.forEach((c) => {
      if (!menuGlobal.find((m) => m.id === c.id)) menuGlobal.push(c);
    });
    container.innerHTML = itens.map(createComboCard).join("");
    atualizarBotoesMenu();
  } catch (e) {
    container.innerHTML = "<p>Erro ao carregar combos</p>";
  }
}

// site/js/main.js

async function initBebidas() {
  const grid = document.getElementById("bebidas-grid");
  if (!grid) return;

  try {
    const itens = await fetchBebidas();

    // Adiciona ao menu global para o carrinho funcionar
    itens.forEach((b) => {
      if (!menuGlobal.find((m) => m.id === b.id)) menuGlobal.push(b);
    });

    if (itens.length === 0) {
      grid.innerHTML = "<p>Nenhuma bebida cadastrada.</p>";
      return;
    }

    // Usa a mesma função de card dos lanches (createMenuItemCard)
    grid.innerHTML = itens.map(createMenuItemCard).join("");

    // Atualiza os botões (caso já tenha algo no carrinho)
    atualizarBotoesMenu();
  } catch (e) {
    grid.innerHTML = "<p>Erro ao carregar bebidas</p>";
  }
}

// --- 4. MODAL DE PRODUTO ---

function abrirModalProduto(produto, qtd, qtdId) {
  const modal = document.getElementById("modal-personalizacao");
  document.body.style.overflow = "hidden";

  itemEmPersonalizacao = {
    produto: produto,
    qtd: qtd,
    qtdIdCard: qtdId,
    selecoes: {
      carnes: [],
      adicionais: [],
      acompanhamentos: [],
      bebidas: [],
    },
    precoBase: produto.price,
    precoTotal: produto.price,
  };

  // Preenche UI
  document.getElementById("modal-img").src = produto.image;
  document.getElementById("modal-title").innerText = produto.name;
  document.getElementById("modal-desc").innerText = produto.description;
  document.getElementById("modal-obs").value = "";

  // Renderiza Seções
  const d = produto.details || {};
  renderSection(
    "lista-carnes",
    "modal-carnes-section",
    d.carnes,
    "radio",
    "carne"
  );
  renderSection(
    "lista-adicionais",
    "modal-adicionais-section",
    d.adicionais,
    "checkbox",
    "add"
  );
  renderSection(
    "lista-acompanhamentos",
    "modal-acompanhamentos-section",
    d.acompanhamentos,
    "checkbox",
    "acomp"
  );
  renderSection(
    "lista-bebidas",
    "modal-bebidas-section",
    d.bebidas,
    "checkbox",
    "bebida"
  );

  // Auto-select carne
  if (d.carnes?.length > 0) {
    const r = document.querySelector('input[name="carne"]');
    if (r) r.checked = true;
  }
  atualizarSelecaoModal();
  modal.style.display = "flex"; // Mostra o modal
}

function renderSection(divId, secId, list, type, name) {
  const div = document.getElementById(divId);
  const section = document.getElementById(secId); // Pega a seção pelo ID correto

  if (!div || !section) return; // Proteção contra erro

  div.innerHTML = "";

  if (list && list.length > 0) {
    section.style.display = "block";
    list.forEach((item, idx) => {
      const priceTxt =
        item.price > 0 ? `+ R$ ${item.price.toFixed(2).replace(".", ",")}` : "";
      div.innerHTML += `
            <label class="option-row">
                <input type="${type}" name="${name}" value="${idx}" data-price="${item.price}" data-name="${item.nome}" onchange="atualizarSelecaoModal()">
                <div class="option-info"><span>${item.nome}</span><span class="option-price">${priceTxt}</span></div>
            </label>`;
    });
  } else {
    section.style.display = "none";
  }
}

function atualizarSelecaoModal() {
  let extra = 0;
  const s = itemEmPersonalizacao.selecoes;
  s.carnes = [];
  s.adicionais = [];
  s.acompanhamentos = [];
  s.bebidas = [];

  const carne = document.querySelector('input[name="carne"]:checked');
  if (carne) {
    s.carnes.push(carne.dataset.name);
    extra += parseFloat(carne.dataset.price);
  }

  ["add", "acomp", "bebida"].forEach((tipo) => {
    const key =
      tipo === "add"
        ? "adicionais"
        : tipo === "acomp"
        ? "acompanhamentos"
        : "bebidas";
    document.querySelectorAll(`input[name="${tipo}"]:checked`).forEach((c) => {
      s[key].push(c.dataset.name);
      extra += parseFloat(c.dataset.price);
    });
  });

  itemEmPersonalizacao.precoTotal = itemEmPersonalizacao.precoBase + extra;
  const total = itemEmPersonalizacao.precoTotal * itemEmPersonalizacao.qtd;
  document.getElementById("modal-total").innerText = `R$ ${total
    .toFixed(2)
    .replace(".", ",")}`;
}

function adicionarItemDoModal() {
  if (
    document.getElementById("modal-carnes-section").style.display !== "none" &&
    itemEmPersonalizacao.selecoes.carnes.length === 0
  ) {
    return showToast("Escolha uma carne!");
  }

  let nome = itemEmPersonalizacao.produto.name;
  const extras = [
    ...itemEmPersonalizacao.selecoes.carnes,
    ...itemEmPersonalizacao.selecoes.adicionais,
    ...itemEmPersonalizacao.selecoes.acompanhamentos,
    ...itemEmPersonalizacao.selecoes.bebidas,
  ];
  if (extras.length) nome += ` (${extras.join(", ")})`;
  const obs = document.getElementById("modal-obs").value;
  if (obs) nome += ` [Obs: ${obs}]`;

  const dadosExtras = {
    productId: itemEmPersonalizacao.produto.id,
    details: {
      carnes: itemEmPersonalizacao.selecoes.carnes,
      adicionais: itemEmPersonalizacao.selecoes.adicionais,
      acompanhamentos: itemEmPersonalizacao.selecoes.acompanhamentos,
      bebidas: itemEmPersonalizacao.selecoes.bebidas,
      obs: obs,
    },
  };

  for (let i = 0; i < itemEmPersonalizacao.qtd; i++) {
    adicionarAoCarrinho(nome, itemEmPersonalizacao.precoTotal, dadosExtras);
  }

  // Reset visual qtd
  const disp = document.getElementById(`qty-${itemEmPersonalizacao.qtdIdCard}`);
  if (disp) disp.innerText = "1";

  fecharModal();
}

function fecharModal() {
  document.getElementById("modal-personalizacao").style.display = "none";
  document.body.style.overflow = "";
}

function mudarQtdModal(delta) {
  // Essa função faltava no HTML que te passei antes, mas é bom ter se usar botões dentro do modal
}

// --- HELPERS ---
function getSafeId(name) {
  return name.replace(/[^a-zA-Z0-9]/g, "_");
}
function alterarQuantidade(id, delta) {
  const el = document.getElementById(`qty-${id}`);
  if (el) el.innerText = Math.max(1, parseInt(el.innerText) + delta);
}
function alterarQuantidadeCarrinho(nome, delta) {
  const item = carrinho.find((i) => i.nome === nome);
  if (item) {
    item.quantity += delta;
    if (item.quantity <= 0) carrinho = carrinho.filter((i) => i.nome !== nome);
  }
  atualizarCarrinhoUI();
  atualizarBotoesMenu();
  salvarCarrinhoLocal();
}
function atualizarBotoesMenu() {
  document.querySelectorAll(".btn-add-item").forEach((btn) => {
    const nome = btn.getAttribute("data-name");
    const qtd = carrinho
      .filter((i) => i.nome.startsWith(nome))
      .reduce((a, b) => a + b.quantity, 0);
    if (qtd > 0) {
      btn.innerHTML = `Adicionado (${qtd})`;
      btn.style.background = "var(--color-gold)";
      btn.style.color = "var(--color-black)";
    } else {
      btn.innerText = btn.classList.contains("btn-primary")
        ? "Eu Quero!"
        : "Adicionar";
      btn.style.background = "";
      btn.style.color = "";
    }
  });
}
function animarCarrinho() {
  const btn = document.getElementById("cart-btn");
  btn?.classList.remove("cart-bump");
  void btn?.offsetWidth;
  btn?.classList.add("cart-bump");
}
function initMobileMenu() {
  const btn = document.querySelector(".hamburger");
  const menu = document.querySelector(".nav-links");
  btn?.addEventListener("click", () => {
    menu.style.display = menu.style.display === "flex" ? "none" : "flex";
  });
}
function initScrollEffects() {
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      // 1. Pega o href dentro do clique
      const href = a.getAttribute("href");

      // 2. Se for apenas "#" (link vazio), ignora e previne o pulo de página
      if (href === "#") {
        e.preventDefault();
        return;
      }
      try {
        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: "smooth" });
        }
      } catch (error) {
        // Se o seletor for inválido, ignora silenciosamente
        console.warn("Link inválido para scroll:", href);
      }
    });
  });
}
function createMenuItemCard(item) {
  const safeId = getSafeId(item.name);
  return `<div class="menu-item">
        <img src="${item.image}" alt="${
    item.name
  }" class="menu-img" loading="lazy">
        <div class="menu-info">
            <h3>${item.name}</h3><p>${item.description}</p>
            <span class="price">R$ ${item.price
              .toFixed(2)
              .replace(".", ",")}</span>
            <div class="quantity-controls">
                <button class="qty-btn" onclick="alterarQuantidade('${safeId}', -1)">-</button>
                <span id="qty-${safeId}" class="qty-display">1</span>
                <button class="qty-btn" onclick="alterarQuantidade('${safeId}', 1)">+</button>
            </div>
            <button class="btn-outline btn-add-item" data-name="${
              item.name
            }" onclick="verificarOpcoes('${
    item.id
  }', '${safeId}')">Adicionar</button>
        </div>
    </div>`;
}
function createComboCard(item) {
  const safeId = getSafeId(item.name);
  return `<div class="menu-item combo-item">
        <img src="${item.image}" alt="${
    item.name
  }" class="menu-img" loading="lazy">
        <div class="menu-info">
            <h3 class="text-gold">${item.name}</h3><p>${item.description}</p>
            <span class="price">R$ ${item.price
              .toFixed(2)
              .replace(".", ",")}</span>
            <div class="quantity-controls">
                <button class="qty-btn-combo" onclick="alterarQuantidade('${safeId}', -1)">-</button>
                <span id="qty-${safeId}" class="qty-display">1</span>
                <button class="qty-btn-combo" onclick="alterarQuantidade('${safeId}', 1)">+</button>
            </div>
            <button class="btn-primary btn-add-item" data-name="${
              item.name
            }" onclick="verificarOpcoes('${
    item.id
  }', '${safeId}')">Eu Quero!</button>
        </div>
    </div>`;
}

// site/js/main.js

async function initBairrosSelect() {
  // 1. Busca lista da API
  const bairros = await fetchNeighborhoodsPublic();

  // Gera o HTML das opções
  let optionsHtml =
    '<option value="" disabled selected>Selecione seu Bairro...</option>';

  if (bairros.length === 0) {
    optionsHtml +=
      '<option value="" disabled>Nenhum bairro cadastrado</option>';
  } else {
    bairros.forEach((b) => {
      optionsHtml += `<option value="${b.name}" data-price="${b.price}">${b.name}</option>`;
    });
  }

  // --- PREENCHE O SELECT DO CHECKOUT (Cálculo de Frete) ---
  const selectCheckout = document.getElementById("bairro");
  if (selectCheckout) {
    selectCheckout.innerHTML = optionsHtml;

    // Evento específico do checkout (Atualizar taxa)
    selectCheckout.addEventListener("change", function () {
      const option = this.options[this.selectedIndex];
      taxaEntregaAtual = parseFloat(option.getAttribute("data-price") || 0);
      const display = document.getElementById("delivery-fee-display");
      if (display) {
        display.innerText = `R$ ${taxaEntregaAtual
          .toFixed(2)
          .replace(".", ",")}`;
      }
    });
  }

  // --- PREENCHE O SELECT DO MODAL "MEUS ENDEREÇOS" (Apenas cadastro) ---
  const selectNovoEnd = document.getElementById("new-bairro-select");
  if (selectNovoEnd) {
    selectNovoEnd.innerHTML = optionsHtml;
    // Aqui não precisa calcular taxa, é só para salvar o nome
  }
  const selectElement = document.getElementById("new-bairro-select");
  if (selectElement) {
    selectElement.addEventListener("change", function () {
      // Quando seleciona algo, muda a cor para branco (texto normal)
      this.style.color = "var(--color-text)";
    });
  }
}

function initContactForm() {
  const form = document.getElementById("contact-form");
  if (!form) return;

  // Elementos do Formulário
  const phoneInput = document.getElementById("phone"); // Use ID para garantir
  const retiradaCheck = document.getElementById("retirada-check");
  const addressSection = document.querySelector(".address-section");

  const toggleAddress = () => {
    if (!retiradaCheck || !addressSection) return;
    const bairroSelect = document.getElementById("bairro"); // Pega o select

    if (retiradaCheck.checked) {
      addressSection.style.display = "none"; // Esconde endereço

      // Remove obrigatoriedade dos inputs escondidos
      addressSection
        .querySelectorAll("input")
        .forEach((i) => i.removeAttribute("required"));

      // [CORREÇÃO] Remove obrigatoriedade do Select de Bairro
      if (bairroSelect) bairroSelect.removeAttribute("required");
    } else {
      addressSection.style.display = "block"; // Mostra endereço

      // Devolve a obrigatoriedade dos inputs
      addressSection.querySelectorAll("input").forEach((i) => {
        if (i.name !== "comp") i.setAttribute("required", "true");
      });

      // [CORREÇÃO] Devolve obrigatoriedade do Bairro
      if (bairroSelect) bairroSelect.setAttribute("required", "true");
    }
  };

  // 1. LÓGICA DA RETIRADA (Corrigida)
  if (retiradaCheck && addressSection) {
    // Função interna para alternar visibilidade
    // Função interna para alternar visibilidade

    // Ouve o clique
    retiradaCheck.addEventListener("change", toggleAddress);

    // Roda uma vez ao carregar (caso o navegador tenha guardado o estado checked)
    toggleAddress();
  } else {
    console.warn(
      "Alerta: Checkbox de retirada ou seção de endereço não encontrados."
    );
  }

  // 2. MÁSCARA DE TELEFONE
  if (phoneInput) {
    phoneInput.addEventListener("input", (e) => {
      let v = e.target.value.replace(/\D/g, "");
      if (v.length > 11) v = v.slice(0, 11);
      if (v.length > 2) v = `(${v.substring(0, 2)}) ${v.substring(2)}`;
      if (v.length > 7) v = `${v.substring(0, 10)}-${v.substring(10)}`;
      e.target.value = v;
    });
  }

  // 3. ENVIO DO FORMULÁRIO
  // --- SUBSTIUA O SEU 'form.addEventListener' ATUAL POR ESTE BLOCO COMPLETO ---
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // 1. Validações Iniciais (Antes de abrir o modal)

    // Verifica se a loja está aberta
    if (!lojaAberta) {
      document.getElementById("modal-closed").style.display = "flex";
      return;
    }

    // Verifica Login
    const { token } = getSession();
    if (!token) {
      abrirModalLogin(
        "Para finalizar o pedido, é necessário entrar ou cadastrar-se."
      );
      return;
    }

    // Validações de Campos
    const name = document.getElementById("name").value;
    const phone = document.getElementById("phone").value;
    const isRetirada = retiradaCheck ? retiradaCheck.checked : false;

    if (name.length < 3) return showToast("Por favor, digite seu nome.");
    if (phone.length < 14) return showToast("Digite um WhatsApp válido.");
    if (carrinho.length === 0)
      return showToast("Seu carrinho está vazio!", "warning");

    // Validação de Endereço (se não for retirada)
    if (!isRetirada) {
      const rua = document.getElementById("address").value;
      const num = document.getElementById("number").value;
      const bairro = document.getElementById("bairro").value;
      if (!rua || !num || !bairro)
        return showToast(
          "Preencha o endereço completo para entrega.",
          "warning"
        );
    }

    // ============================================================
    // AQUI ENTRA A LÓGICA DO MODAL
    // ============================================================

    // Verifica se o formulário já tem a "bandeira" de confirmado
    if (form.getAttribute("data-confirmed") === "true") {
      // --- CENÁRIO A: JÁ CONFIRMADO PELO MODAL (ENVIO REAL) ---

      // Remove a bandeira para o próximo pedido
      form.removeAttribute("data-confirmed");

      // Identifica qual botão clicou (Sistema ou WhatsApp)
      // Nota: Ao usar requestSubmit() do modal, o 'submitter' pode se perder em alguns browsers,
      // mas vamos assumir o padrão do sistema se não detectado.
      const btnClicado = e.submitter;
      const deveAbrirZap =
        btnClicado && btnClicado.id === "btn-submit-whatsapp";

      // Feedback Visual no Botão (se possível identificar)
      if (btnClicado) {
        btnClicado.innerText = "Enviando...";
        btnClicado.disabled = true;
      } else {
        // Fallback visual no botão principal se o submitter não for detectado
        const btnMain = document.getElementById("btn-submit-system");
        if (btnMain) {
          btnMain.innerText = "Enviando...";
          btnMain.disabled = true;
        }
      }

      // --- PREPARAÇÃO DOS DADOS (CÓDIGO ORIGINAL SEU) ---
      const totalProdutos = carrinho.reduce(
        (a, b) => a + b.preco * b.quantity,
        0
      );
      let totalFinal = totalProdutos + taxaEntregaAtual;

      // Recalcula desconto para garantir precisão
      let desconto = 0;
      if (cupomSelecionado) {
        const subtotal = carrinho.reduce(
          (acc, item) => acc + item.preco * item.quantity,
          0
        );
        if (cupomSelecionado.discount_percent > 0) {
          desconto = subtotal * (cupomSelecionado.discount_percent / 100);
        } else {
          desconto = cupomSelecionado.discount_fixed;
        }
        if (desconto > subtotal) desconto = subtotal;
      }
      totalFinal = totalFinal - desconto;

      const resumoTexto = carrinho
        .map((i) => `${i.quantity}x ${i.nome}`)
        .join("\n");

      // Captura Pagamento
      const paymentEl = document.querySelector(
        'input[name="paymentMethod"]:checked'
      );
      let paymentMethod = paymentEl ? paymentEl.value : "Não informado";
      if (paymentMethod === "cash") {
        const trocoVal = document.getElementById("troco-for")?.value;
        if (trocoVal) paymentMethod += ` (Troco para ${trocoVal})`;
      }

      const frontData = {
        name: name,
        phone: phone,
        address: isRetirada
          ? "RETIRADA NO LOCAL"
          : document.getElementById("address").value,
        number: isRetirada ? "0" : document.getElementById("number").value,
        bairro: isRetirada ? "-" : document.getElementById("bairro").value,
        comp: isRetirada ? "" : document.getElementById("comp").value,
        message: document.getElementById("message").value,
        payment_method: paymentMethod,
        resumoCarrinho: resumoTexto,
        cartItems: carrinho,
        total: totalFinal,
        coupon_code: cupomSelecionado ? cupomSelecionado.code : null,
      };

      // --- ENVIO API (CÓDIGO ORIGINAL SEU) ---
      try {
        const res = await submitOrder(frontData, deveAbrirZap);

        if (res.success) {
          if (!deveAbrirZap)
            showToast(`Pedido #${res.orderId} enviado com sucesso!`, "success");

          // Limpeza Segura (Sua correção anterior)
          fecharModalConfirmacao();
          carrinho = [];
          cupomSelecionado = null;
          atualizarVisualDesconto();
          salvarCarrinhoLocal();
          atualizarCarrinhoUI();
          atualizarBotoesMenu();
          form.reset();
          checkLoginState();

          if (isRetirada && retiradaCheck) {
            retiradaCheck.checked = false;
            const addressSection = document.querySelector(".address-section");
            if (addressSection) addressSection.style.display = "block";
          }
        } else {
          showToast("Erro ao enviar: " + res.error, "error");
        }
      } catch (error) {
        console.error(error);
        showToast("Erro técnico ao enviar pedido.", "error");
      } finally {
        // Restaura botões
        if (btnClicado) {
          btnClicado.innerText = deveAbrirZap ? "WhatsApp" : "Fazer Pedido";
          btnClicado.disabled = false;
        } else {
          const btnMain = document.getElementById("btn-submit-system");
          if (btnMain) {
            btnMain.innerText = "Fazer Pedido";
            btnMain.disabled = false;
          }
        }
      }
    } else {
      // --- CENÁRIO B: NÃO CONFIRMADO -> ABRE O MODAL ---

      // Detecta se foi clique no WhatsApp (se for Zap, talvez você não queira modal,
      // mas aqui vamos abrir o modal para ambos por segurança)
      abrirModalConfirmacao();
    }
  });
}

async function initHorarioFuncionamento() {
  const statusBox = document.getElementById("status-funcionamento");
  const statusText = statusBox ? statusBox.querySelector(".status-text") : null;

  // 1. Busca horários do banco se ainda não tiver
  if (horariosGlobal.length === 0) {
    horariosGlobal = await fetchSchedule();
  }

  // Se falhar a busca, usa um fallback seguro (fechado ou horário padrão)
  if (horariosGlobal.length === 0) {
    console.warn("Não foi possível carregar horários. Usando padrão.");
    // Fallback manual se quiser, ou deixa vazio para tentar de novo
  }

  const agora = new Date();
  const diaHoje = agora.getDay(); // 0-6
  const minsAgora = agora.getHours() * 60 + agora.getMinutes();

  // 2. Encontra a regra de hoje
  const regraHoje = horariosGlobal.find((d) => d.day_of_week === diaHoje);

  let estaAberto = false;
  let texto = "Fechado";

  if (regraHoje) {
    if (regraHoje.is_closed) {
      estaAberto = false;
      texto = "Fechado hoje";
    } else {
      // Converte "18:30" para minutos (18*60 + 30 = 1110)
      const [hAbre, mAbre] = regraHoje.open_time.split(":").map(Number);
      const [hFecha, mFecha] = regraHoje.close_time.split(":").map(Number);

      const minAbre = hAbre * 60 + mAbre;
      let minFecha = hFecha * 60 + mFecha;

      // Tratamento para madrugada (ex: fecha as 01:00 do dia seguinte)
      // Se fecha menor que abre (ex: abre 18:00 fecha 01:00), somamos 24h ao fecha
      if (minFecha < minAbre) minFecha += 24 * 60;

      // Ajuste se já passou da meia noite (agora é 00:30, mas pertence ao turno de ontem)
      // Isso é complexo. Para simplificar no seu modelo "diário":
      // Vamos assumir funcionamento no mesmo dia ou até o final da noite.

      estaAberto = minsAgora >= minAbre && minsAgora < minFecha;

      texto = estaAberto
        ? `Aberto • Fecha às ${regraHoje.close_time}`
        : `Fechado • Abre às ${regraHoje.open_time}`;
    }
  }

  // Atualiza Global
  lojaAberta = estaAberto;
  // lojaAberta = true; // DEBUG: Descomente para testar aberto forçado

  // Atualiza UI
  if (statusBox && statusText) {
    statusBox.className =
      "status-box " + (lojaAberta ? "status-open" : "status-closed");
    statusText.innerText = texto;
  }

  // Re-executa a cada minuto
  setTimeout(initHorarioFuncionamento, 60000);
}
// --- MINHA CONTA ---

function openAccountModal() {
  const { user } = getSession();
  if (!user.id) return showToast("Faça login novamente.");

  // Preenche o formulário com o que temos salvo
  document.getElementById("acc-name").value = user.name || "";
  document.getElementById("acc-email").value = user.email || "";
  document.getElementById("acc-whatsapp").value = user.whatsapp || "";
  document.getElementById("acc-password").value = ""; // Senha sempre vazia por segurança

  document.getElementById("modal-account").style.display = "flex";
  toggleProfileMenu(); // Fecha o menu dropdown
}

function closeAccountModal() {
  document.getElementById("modal-account").style.display = "none";
}

async function saveAccountDetails() {
  const btn = document.querySelector("#modal-account .btn-primary");
  const originalTxt = btn.innerText;

  // Campos
  const pass = document.getElementById("acc-password").value;
  const confirm = document.getElementById("acc-password-confirm").value;

  // 1. Validação de Senha
  if (pass) {
    const check = validarForcaSenha(pass);
    if (!check.valid) {
      return showToast("Senha muito fraca: " + check.msg, "warning");
    }
    if (pass !== confirm) {
      return showToast("As senhas não conferem!", "warning");
    }
  }

  btn.innerText = "Salvando...";
  btn.disabled = true;

  const data = {
    name: document.getElementById("acc-name").value,
    whatsapp: document.getElementById("acc-whatsapp").value, // Captura o Zap
    password: pass || undefined,
  };

  const res = await updateUserProfile(data);

  if (res.success) {
    // Pega a sessão antiga
    const { user: oldUser } = getSession();

    // Mescla os dados antigos com os novos que vieram do backend
    const newUser = { ...oldUser, ...res.user };

    // [CORREÇÃO CRÍTICA] Salva a nova versão no navegador!
    // Antes, essa linha não existia, por isso o dado sumia ao recarregar
    saveSession(null, newUser);

    // Atualiza a tela imediatamente
    checkLoginState();

    showToast("Dados atualizados com sucesso!", "success");

    // Limpa campos de senha
    document.getElementById("acc-password").value = "";
    document.getElementById("acc-password-confirm").value = "";
    document.getElementById("acc-strength").innerText = "";

    closeAccountModal();
  } else {
    showToast("Erro: " + res.error, "error");
  }

  btn.innerText = originalTxt;
  btn.disabled = false;
}
function toggleMobileMenu() {
  const navLinks = document.querySelector(".nav-links");
  if (navLinks) {
    navLinks.classList.toggle("active"); // Usa classe CSS para abrir/fechar
  }
}

// Garante que ao clicar num link, o menu feche (UX Mobile)
document.querySelectorAll(".nav-links a").forEach((link) => {
  link.addEventListener("click", () => {
    const navLinks = document.querySelector(".nav-links");
    if (navLinks) navLinks.classList.remove("active");
  });
});

// Adicione no final do main.js

// --- GESTÃO DE ENDEREÇOS ---

async function openAddressesModal() {
  document.getElementById("modal-addresses").style.display = "flex";
  toggleProfileMenu(); // fecha menu
  carregarListaEnderecos();
}

function closeAddressesModal() {
  document.getElementById("modal-addresses").style.display = "none";
  document.getElementById("form-new-address").style.display = "none";
}

function toggleAddAddressForm() {
  const form = document.getElementById("form-new-address");
  form.style.display = form.style.display === "none" ? "block" : "none";
}

async function carregarListaEnderecos() {
  const container = document.getElementById("address-list-container");
  container.innerHTML = '<p style="color:#ccc">Carregando...</p>';

  const enderecos = await fetchAddresses();
  container.innerHTML = "";

  if (enderecos.length === 0) {
    container.innerHTML =
      '<p style="color:#ccc">Nenhum endereço cadastrado.</p>';
    return;
  }

  enderecos.forEach((addr) => {
    const isActive = addr.is_active;
    const cardClass = isActive ? "address-card active" : "address-card";
    const btnHtml = isActive
      ? `<span style="color:#2ecc71; font-weight:bold;"><i class="fa-solid fa-check"></i> Ativo</span>`
      : `<button class="btn-outline btn-sm" onclick="selecionarEnderecoAtivo(${addr.id})">Usar este</button>`;

    container.innerHTML += `
            <div class="${cardClass}">
                <div>
                    <strong>${addr.street}, ${addr.number}</strong><br>
                    <small>${addr.neighborhood} ${
      addr.complement ? "- " + addr.complement : ""
    }</small>
                </div>
                <div style="display:flex; gap:10px; align-items:center;">
                    ${btnHtml}
                    <button class="remove-btn" onclick="excluirEndereco(${
                      addr.id
                    })"><i class="fa-solid fa-trash"></i></button>
                </div>
            </div>
        `;
  });

  // [MÁGICA] Atualiza o formulário de checkout com o endereço ativo
  preencherCheckoutComAtivo(enderecos);
}

function preencherCheckoutComAtivo(enderecos) {
  const ativo = enderecos.find((a) => a.is_active);

  // 1. Preenche os campos de texto
  if (ativo) {
    if (document.getElementById("address"))
      document.getElementById("address").value = ativo.street;
    if (document.getElementById("number"))
      document.getElementById("number").value = ativo.number;
    if (document.getElementById("comp"))
      document.getElementById("comp").value = ativo.complement || "";

    // 2. Seleciona o Bairro e FORÇA o cálculo da taxa
    const bairroSelect = document.getElementById("bairro");
    if (bairroSelect) {
      bairroSelect.value = ativo.neighborhood;

      // Truque: Simula que o usuário mudou manualmente para atualizar a variável global
      const option = bairroSelect.options[bairroSelect.selectedIndex];
      if (option) {
        taxaEntregaAtual = parseFloat(option.getAttribute("data-price") || 0);

        // Atualiza o display visual da taxa no formulário (se existir)
        const displayFee = document.getElementById("delivery-fee-display");
        if (displayFee) {
          displayFee.innerText = `R$ ${taxaEntregaAtual
            .toFixed(2)
            .replace(".", ",")}`;
        }
      }
    }
  }
}

async function selecionarEnderecoAtivo(id) {
  await setActiveAddress(id);
  carregarListaEnderecos(); // Recarrega para atualizar visual e checkout
}

async function excluirEndereco(id) {
  if (confirm("Remover este endereço?")) {
    await deleteAddress(id);
    carregarListaEnderecos();
  }
}

// Listener do Form de Novo Endereço
// site/js/main.js

const formNewAddr = document.getElementById("form-new-address");
if (formNewAddr) {
  formNewAddr.addEventListener("submit", async (e) => {
    e.preventDefault();

    // [CORREÇÃO] Pega o valor do SELECT novo
    const bairroSelect = document.getElementById("new-bairro-select");
    const bairroValor = bairroSelect ? bairroSelect.value : "";

    if (!bairroValor) {
      return showToast("Selecione um bairro válido.", "warning");
    }

    const data = {
      street: document.getElementById("new-street").value,
      number: document.getElementById("new-number").value,
      neighborhood: bairroValor, // Usa o valor do dropdown
      complement: document.getElementById("new-comp").value,
    };

    const ok = await addAddress(data);
    if (ok) {
      formNewAddr.reset();
      formNewAddr.style.display = "none";
      carregarListaEnderecos();
      showToast("Endereço salvo com sucesso!", "success");
    } else {
      showToast("Erro ao salvar endereço", "error");
    }
  });
}
let ordersInterval = null;
// --- HISTÓRICO DE PEDIDOS ---

// site/js/main.js

async function abrirHistoricoPedidos() {
  const { user } = getSession();
  if (!user.id) return showToast("Faça login para ver.", "warning");

  const modal = document.getElementById("modal-orders");
  const cont = document.getElementById("orders-list-container");

  modal.style.display = "flex";
  toggleProfileMenu();

  // Mostra loading apenas na abertura inicial
  cont.innerHTML =
    '<div class="loading-spinner" style="margin:20px auto;"></div>';

  // Função interna que busca e desenha (será chamada repetidamente)
  const atualizarLista = async () => {
    const pedidos = await fetchMyOrders();

    if (!pedidos.length) {
      cont.innerHTML =
        '<p style="text-align:center; padding:20px; color:#888;">Nenhum pedido encontrado.</p>';
      return;
    }

    // Renderiza a lista
    cont.innerHTML = pedidos
      .map((p) => {
        const date = new Date(p.date_created).toLocaleDateString("pt-BR", {
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        });

        // [CORREÇÃO] Converte o total do pedido para número
        const totalPedido = parseFloat(p.total_price);

        return `
            <div class="order-card">
                <div class="order-header">
                    <span>#${p.id} - ${date}</span>
                    <span class="status-badge st-${getStatusClass(p.status)}">${
          p.status
        }</span>
                </div>
                <div class="order-body">
                    ${p.items
                      .map((i) => {
                        // [CORREÇÃO] Converte o preço do item para número antes do toFixed
                        const precoItem = parseFloat(i.price_at_time);

                        return `<div class="order-item-row">
                            <span>${i.quantity}x ${i.product.name}</span>
                            <span>R$ ${precoItem
                              .toFixed(2)
                              .replace(".", ",")}</span>
                         </div>`;
                      })
                      .join("")}
                </div>
                <div class="order-footer">
                    <span>Total:</span>
                    <span class="order-total">R$ ${totalPedido
                      .toFixed(2)
                      .replace(".", ",")}</span>
                </div>
            </div>`;
      })
      .join("");
  };

  // 1. Chama imediatamente para não esperar 2s na primeira vez
  await atualizarLista();

  // 2. Inicia o Loop (Polling) a cada 2 segundos
  if (ordersInterval) clearInterval(ordersInterval); // Segurança
  ordersInterval = setInterval(atualizarLista, 2000);
}

function fecharModalPedidos() {
  document.getElementById("modal-orders").style.display = "none";

  // PARAR O RELOAD QUANDO FECHAR (Importante!)
  if (ordersInterval) {
    clearInterval(ordersInterval);
    ordersInterval = null;
  }
}

function getStatusClass(st) {
  if (st === "Recebido") return "received";
  if (st === "Em Preparo") return "prep";
  if (st === "Saiu para Entrega") return "delivery";
  if (st === "Concluído") return "done";
  return "canceled";
}
function renderizarPedidos(lista) {
  const container = document.getElementById("orders-list-container");
  container.innerHTML = "";

  if (lista.length === 0) {
    container.innerHTML = `
            <div style="text-align:center; padding:30px; color:#888;">
                <i class="fa-solid fa-burger" style="font-size:3rem; margin-bottom:10px;"></i>
                <p>Você ainda não fez nenhum pedido.</p>
                <button class="btn-outline mt-3" onclick="fecharModalPedidos()">Ver Cardápio</button>
            </div>`;
    return;
  }

  lista.forEach((pedido) => {
    const dataFormatada = new Date(pedido.date_created).toLocaleDateString(
      "pt-BR",
      {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }
    );

    // Traduz status para classe CSS (cor) e Ícone
    const statusConfig = getStatusConfig(pedido.status);

    // Monta resumo dos itens (Ex: 2x X-Burger, 1x Coca)
    const resumoItens = pedido.items
      .map(
        (i) =>
          `<div class="order-item-row">
                <span>${i.quantity}x ${i.product.name}</span>
                <span style="color:#aaa;">R$ ${i.price_at_time.toFixed(
                  2
                )}</span>
             </div>`
      )
      .join("");

    const html = `
            <div class="order-card">
                <div class="order-header">
                    <div>
                        <span class="order-id">Pedido #${pedido.id}</span>
                        <span class="order-date">${dataFormatada}</span>
                    </div>
                    <span class="status-badge ${statusConfig.css}">
                        ${statusConfig.icon} ${pedido.status}
                    </span>
                </div>
                
                <div class="order-body">
                    ${resumoItens}
                </div>

                <div class="order-footer">
                    <span>Total:</span>
                    <span class="order-total">R$ ${pedido.total_price
                      .toFixed(2)
                      .replace(".", ",")}</span>
                </div>
            </div>
        `;
    container.innerHTML += html;
  });
}

function getStatusConfig(status) {
  switch (status) {
    case "Recebido":
      return {
        css: "st-received",
        icon: '<i class="fa-regular fa-clock"></i>',
      };
    case "Em Preparo":
      return {
        css: "st-prep",
        icon: '<i class="fa-solid fa-fire-burner"></i>',
      };
    case "Saiu para Entrega":
      return {
        css: "st-delivery",
        icon: '<i class="fa-solid fa-motorcycle"></i>',
      };
    case "Concluído":
      return { css: "st-done", icon: '<i class="fa-solid fa-check"></i>' };
    case "Cancelado":
      return {
        css: "st-canceled",
        icon: '<i class="fa-solid fa-xmark"></i>',
      };
    default:
      return { css: "", icon: "" };
  }
}

// --- FUNÇÃO DE VALIDAÇÃO DE SENHA ---
function validarForcaSenha(senha) {
  const minLength = 8;
  const hasUpper = /[A-Z]/.test(senha);
  const hasLower = /[a-z]/.test(senha);
  const hasNumber = /[0-9]/.test(senha);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(senha);

  if (senha.length < minLength)
    return { valid: false, msg: "Mínimo 8 caracteres" };
  if (!hasUpper) return { valid: false, msg: "Precisa de letra maiúscula" };
  if (!hasLower) return { valid: false, msg: "Precisa de letra minúscula" };
  if (!hasNumber) return { valid: false, msg: "Precisa de um número" };
  if (!hasSpecial)
    return { valid: false, msg: "Precisa de caractere especial (!@#...)" };

  return { valid: true, msg: "Senha Forte 💪" };
}

function mostrarForcaSenha(valor, elementoId) {
  const el = document.getElementById(elementoId);
  if (!valor) {
    el.innerText = "";
    el.className = "password-strength";
    return;
  }

  const resultado = validarForcaSenha(valor);
  el.innerText = resultado.msg;

  if (resultado.valid) {
    el.className = "password-strength strength-strong";
  } else {
    // Se tiver pelo menos 6 chars, amarela, senão vermelha
    el.className =
      valor.length > 5
        ? "password-strength strength-medium"
        : "password-strength strength-weak";
  }
}

// --- CHAT ---

let chatInterval = null;
let chatAberto = false; // Estado do chat (aberto/fechado)
let ultimoEnvio = 0;
const COOLDOWN_CHAT = 2000; // Tempo de espera entre mensagens
let historicoCarregado = false; // Controle para não carregar histórico repetidamente sem necessidade

// Função para abrir/fechar o chat
function toggleChat() {
  const widget = document.getElementById("chat-widget");
  const icon = document.getElementById("chat-icon");
  const { user } = getSession();

  // 1. Validação de Login
  if (!user.id) return showToast("Faça login para usar o chat.");

  // Verifica se o chat está minimizado (fechado)
  const estaFechado = widget.classList.contains("minimized");

  if (estaFechado) {
    // --- ABRINDO O CHAT ---
    widget.classList.remove("minimized");

    // Atualiza ícone
    icon.classList.remove("fa-chevron-up");
    icon.classList.add("fa-chevron-down");

    // [CORREÇÃO IMPORTANTE]: Atualiza o estado da variável para TRUE
    chatAberto = true;

    // Carrega o histórico apenas se ainda não foi carregado nesta sessão
    if (!historicoCarregado) {
      carregarMensagens();
      historicoCarregado = true;
    }

    // Foca no input para digitar rápido
    setTimeout(() => {
      const input = document.getElementById("chat-input");
      if (input) input.focus();
    }, 300);
  } else {
    // --- FECHANDO O CHAT ---
    widget.classList.add("minimized");

    // Atualiza ícone
    icon.classList.remove("fa-chevron-down");
    icon.classList.add("fa-chevron-up");

    // [CORREÇÃO]: Atualiza estado para FALSE
    chatAberto = false;
  }
}

// Função que busca as mensagens antigas no Banco de Dados
async function carregarMensagens() {
  // [CORREÇÃO]: Removemos a verificação rigorosa de (!chatAberto) aqui,
  // pois às vezes o estado visual atualiza antes da variável.
  // Vamos confiar que se essa função foi chamada, é para carregar.

  const container = document.getElementById("chat-messages-area");

  // Feedback visual de carregamento
  container.innerHTML = '<p class="chat-welcome">Carregando histórico...</p>';

  // Busca mensagens na API (routes_chat.py)
  const msgs = await getChatMessages();

  // Limpa o container para renderizar a lista oficial
  container.innerHTML = '<p class="chat-welcome">Histórico de Conversa</p>';

  if (msgs.length === 0) {
    container.innerHTML +=
      '<p style="text-align:center; color:#888; font-size:0.8rem;">Nenhuma mensagem ainda.</p>';
  }

  // Renderiza cada mensagem
  msgs.forEach((msg) => {
    // Determina se a mensagem é do admin ou do cliente para estilizar (direita/esquerda)
    const classe = msg.is_from_admin ? "msg-admin" : "msg-user";

    const div = document.createElement("div");
    div.className = `msg ${classe}`;
    div.innerText = msg.message;

    // Adiciona a hora se disponível (opcional)
    if (msg.timestamp) {
      div.title = new Date(msg.timestamp).toLocaleString();
    }

    container.appendChild(div);
  });

  // [CORREÇÃO]: Rola para o final para ver a última mensagem
  container.scrollTop = container.scrollHeight;
}

// Envia mensagem para o servidor
async function enviarMensagemChat() {
  const input = document.getElementById("chat-input");
  const texto = input.value.trim();

  if (!texto) return;

  if (texto.length > 800) {
    showToast("Sua mensagem é muito longa. Por favor, seja mais breve.");
    return;
  }

  // Controle de Spam (Cooldown) para evitar cliques duplos
  const agora = Date.now();
  if (agora - ultimoEnvio < COOLDOWN_CHAT) {
    return;
  }

  // 1. Envia para o backend via API (POST)
  // Nota: Não desenhamos na tela aqui. Esperamos o Socket.io devolver a mensagem.
  // Isso garante que o que aparece na tela é o que REALMENTE foi salvo no servidor.
  const sucesso = await sendChatMessage(texto);

  if (sucesso) {
    // 2. Limpa o campo
    input.value = "";
    input.focus();
    ultimoEnvio = Date.now();
    // A mensagem aparecerá via Socket (socket.on('chat_message')) configurado no início do main.js
  } else {
    showToast("Erro ao enviar mensagem.", "error");
  }
}

// Adiciona mensagem na tela (usado pelo Socket.IO)
function adicionarMensagemNaTela(msg) {
  const container = document.getElementById("chat-messages-area");
  if (!container) return;

  // Remove aviso de "Nenhuma mensagem" se existir
  if (container.querySelector('p[style*="text-align:center"]')) {
    container.querySelector('p[style*="text-align:center"]').remove();
  }

  const classe = msg.is_from_admin ? "msg-admin" : "msg-user";

  const div = document.createElement("div");
  div.className = `msg ${classe}`;
  div.innerText = msg.message;

  // Adiciona ao final e rola para baixo imediatamente
  container.appendChild(div);

  // Animação suave de scroll
  container.scrollTo({
    top: container.scrollHeight,
    behavior: "smooth",
  });
}

// Atalho de teclado (Enter)
function handleChatKey(e) {
  if (e.key === "Enter") enviarMensagemChat();
}

function toggleTroco(radio) {
  const box = document.getElementById("troco-box");
  if (box) {
    box.style.display =
      radio.checked && radio.value === "cash" ? "block" : "none";
  }
}

// Listener para fechar o troco se clicar em outro meio
document.querySelectorAll('input[name="paymentMethod"]').forEach((radio) => {
  radio.addEventListener("change", (e) => {
    const box = document.getElementById("troco-box");
    if (e.target.value !== "cash" && box) box.style.display = "none";
  });
});

// --- LÓGICA DE CUPONS ---

async function initCoupons() {
  cuponsDisponiveis = await fetchPublicCoupons();
  renderizarCupons();
}

function renderizarCupons() {
  const container = document.getElementById("coupons-container");
  if (!container) return;

  if (cuponsDisponiveis.length === 0) {
    container.innerHTML =
      '<p style="color:#666; font-size:0.9rem;">Nenhum cupom disponível no momento.</p>';
    return;
  }

  // Calcula total atual do carrinho
  const totalCarrinho = carrinho.reduce(
    (acc, item) => acc + item.preco * item.quantity,
    0
  );

  container.innerHTML = cuponsDisponiveis
    .map((c) => {
      let isMinimoAtingido = totalCarrinho >= c.min_purchase;
      const disabledClass = isMinimoAtingido ? "" : "disabled";
      const titleAttr = isMinimoAtingido
        ? ""
        : `Mínimo de R$ ${c.min_purchase.toFixed(2)}`;

      // Texto do desconto
      const descTexto =
        c.discount_percent > 0
          ? `${c.discount_percent}% OFF`
          : `R$ ${c.discount_fixed.toFixed(2)} OFF`;

      return `
            <label class="coupon-wrapper" title="${titleAttr}">
                <input type="radio" name="selectedCoupon" value="${c.code}" 
                    class="coupon-option" 
                    ${!isMinimoAtingido ? "disabled" : ""}
                    onchange="selecionarCupom('${c.code}')">
                
                <div class="coupon-card-ui ${disabledClass}">
                    <span class="cp-code">${c.code}</span>
                    <span class="cp-desc">${descTexto}</span>
                    ${
                      c.min_purchase > 0
                        ? `<span class="cp-min">Mín. R$ ${c.min_purchase.toFixed(
                            2
                          )}</span>`
                        : ""
                    }
                </div>
            </label>
        `;
    })
    .join("");
}

// Torna global para o HTML acessar
window.selecionarCupom = function (code) {
  const cupom = cuponsDisponiveis.find((c) => c.code === code);
  const totalCarrinho = carrinho.reduce(
    (acc, item) => acc + item.preco * item.quantity,
    0
  );

  if (!cupom) return;

  // Validação Frontend (Dupla checagem)
  if (totalCarrinho < cupom.min_purchase) {
    showToast(
      `Valor mínimo para este cupom: R$ ${cupom.min_purchase.toFixed(2)}`,
      "warning"
    );
    // Desmarca
    document.querySelector(`input[value="${code}"]`).checked = false;
    cupomSelecionado = null;
    atualizarVisualDesconto();
    return;
  }

  cupomSelecionado = cupom;
  atualizarVisualDesconto();
  showToast(`Cupom ${code} aplicado!`, "success");
};

function atualizarVisualDesconto() {
  const display = document.getElementById("discount-display");
  const valSpan = document.getElementById("discount-value");

  if (!cupomSelecionado) {
    display.style.display = "none";
    return;
  }

  const totalCarrinho = carrinho.reduce(
    (acc, item) => acc + item.preco * item.quantity,
    0
  );
  let desconto = 0;

  if (cupomSelecionado.discount_percent > 0) {
    desconto = totalCarrinho * (cupomSelecionado.discount_percent / 100);
  } else {
    desconto = cupomSelecionado.discount_fixed;
  }

  // Garante que não desconte mais que o total
  if (desconto > totalCarrinho) desconto = totalCarrinho;

  valSpan.innerText = `- R$ ${desconto.toFixed(2).replace(".", ",")}`;
  display.style.display = "block";
}
// =========================================
//  SISTEMA DE PERSISTÊNCIA (MEMÓRIA)
// =========================================

// 1. Salva o carrinho atual no navegador
function salvarCarrinhoLocal() {
  console.log("💾 Salvando carrinho...", carrinho);
  localStorage.setItem("cegonha_cart", JSON.stringify(carrinho));
}

// 2. Recupera o carrinho quando o site abre
function carregarCarrinhoLocal() {
  const salvo = localStorage.getItem("cegonha_cart");
  if (salvo) {
    carrinho = JSON.parse(salvo);
    console.log("📂 Carrinho recuperado:", carrinho);

    // Atualiza o visual (totais, bolinhas vermelhas, lista lateral)
    atualizarCarrinhoUI();
    atualizarBotoesMenu();
  }
}

window.pedirMagicLink = pedirMagicLink;

// Alterna entre "Magic Link" e "Senha" dentro da aba de Login
function toggleLoginMode(mode) {
  const magicForm = document.getElementById("form-magic-login");
  const passForm = document.getElementById("form-password-login");

  if (mode === "password") {
    magicForm.style.display = "none";
    passForm.style.display = "block";

    // Auto-foco no campo de email se estiver vazio
    const emailMagic = document.getElementById("magic-email").value;
    const emailPass = document.getElementById("login-email");
    if (emailMagic) emailPass.value = emailMagic; // Copia o email digitado
  } else {
    magicForm.style.display = "block";
    passForm.style.display = "none";
  }
}

// ...
// Lembre de exportar a função para o HTML usar:
window.toggleLoginMode = toggleLoginMode;

// site/js/main.js - Substitua o final do arquivo (Funções globais) por isto:

// --- LÓGICA DE ADIÇÃO AO CARRINHO (Unificada) ---

window.verificarOpcoes = function (id) {
  // 1. Busca o produto no menu global (Lanches ou Bebidas)
  // Usa '==' para funcionar se id for string ou numero
  let produto = menuGlobal.find((p) => p.id == id);

  if (!produto) {
    console.error("Produto não encontrado ID:", id);
    return showToast("Erro ao adicionar produto.", "error");
  }

  // Define globalmente
  produtoSelecionado = produto;

  // 2. Verifica se o produto tem opções de personalização no JSON
  const d = produto.details || {};
  const temOpcoes =
    (d.carnes && d.carnes.length > 0) ||
    (d.adicionais && d.adicionais.length > 0) ||
    (d.acompanhamentos && d.acompanhamentos.length > 0) ||
    (d.bebidas && d.bebidas.length > 0); // Bebidas dentro de combos, não a bebida avulsa

  if (temOpcoes) {
    // Se tem opções (ex: Lanche), abre o modal
    const safeId = getSafeId(produto.name);
    // Pega a quantidade que estava no card (input +/-) ou assume 1
    const qtdDisplay = document.getElementById(`qty-${safeId}`);
    const qtd = qtdDisplay ? parseInt(qtdDisplay.innerText) : 1;

    abrirModalProduto(produto, qtd, safeId);
  } else {
    // 3. Se NÃO tem opções (ex: Bebida simples), adiciona direto

    // Pega a quantidade do card
    const safeId = getSafeId(produto.name);
    const qtdDisplay = document.getElementById(`qty-${safeId}`);
    const quantidade = qtdDisplay ? parseInt(qtdDisplay.innerText) : 1;

    const dadosExtras = {
      productId: produto.id,
      details: { obs: "" }, // Detalhes vazios
    };

    // Adiciona N vezes ao carrinho
    // (Poderiamos mudar a lógica do carrinho para aceitar qtd direta, mas para manter compatibilidade:)
    for (let i = 0; i < quantidade; i++) {
      adicionarAoCarrinho(produto.name, produto.price, dadosExtras);
    }

    // Reseta o contador visual para 1
    if (qtdDisplay) qtdDisplay.innerText = "1";
  }
};

// Removemos a função 'adicionarComQuantidade' antiga pois ela estava quebrada e redundante.
// A lógica agora é feita via 'adicionarItemDoModal' (para lanches) ou direta no 'verificarOpcoes' (para bebidas).

window.adicionarAoCarrinho = adicionarAoCarrinho; // Garante exportação

// --- NO FINAL DO ARQUIVO main.js ---

// Define a função diretamente na janela global para evitar erro de escopo
window.abrirModalMagic = function () {
  console.log("Tentando abrir modal Magic Link..."); // Log para debug

  const modal = document.getElementById("modal-magic-link");
  if (modal) {
    modal.classList.add("active"); // Usa classe para mostrar
    modal.style.display = "flex"; // Reforça o display
  } else {
    console.error(
      "ERRO: O HTML do modal #modal-magic-link não foi encontrado!"
    );
    showToast("Verifique seu e-mail! (Modal não encontrado)", "error");
  }
};

window.fecharModalMagic = function () {
  const modal = document.getElementById("modal-magic-link");
  if (modal) {
    modal.classList.remove("active");
    modal.style.display = "none";
  }
};

// --- Lógica do Modal de Confirmação ---

window.fecharModalConfirmacao = function () {
  const modal = document.getElementById("modal-confirm-order");
  if (modal) {
    modal.classList.remove("active");
    modal.style.display = "none"; // Força o desaparecimento
  }
};

window.abrirModalConfirmacao = function () {
  const modal = document.getElementById("modal-confirm-order");
  const container = document.getElementById("confirm-summary-body");

  if (!modal || !container) return;

  // 1. Coletar dados
  const nome = document.getElementById("name").value;
  const telefone = document.getElementById("phone").value;

  const rua = document.getElementById("address").value;
  const numero = document.getElementById("number").value;
  const bairroSelect = document.getElementById("bairro");
  const bairroNome =
    bairroSelect.options[bairroSelect.selectedIndex]?.text || "";
  const complemento = document.getElementById("comp").value;
  const isRetirada = document.getElementById("retirada-check").checked;

  const metodoPagamentoInput = document.querySelector(
    'input[name="paymentMethod"]:checked'
  );
  let metodoPagamento = metodoPagamentoInput
    ? metodoPagamentoInput.parentElement.innerText.trim()
    : "Não informado";

  const trocoVal = document.getElementById("troco-for").value;
  if (
    metodoPagamentoInput &&
    metodoPagamentoInput.value === "cash" &&
    trocoVal
  ) {
    metodoPagamento += ` (Troco p/ ${trocoVal})`;
  }

  // 2. Calcular Totais
  const subtotal = carrinho.reduce(
    (acc, item) => acc + item.preco * item.quantity,
    0
  );
  let desconto = 0;

  if (cupomSelecionado) {
    if (cupomSelecionado.discount_percent > 0) {
      desconto = subtotal * (cupomSelecionado.discount_percent / 100);
    } else {
      desconto = cupomSelecionado.discount_fixed;
    }
    if (desconto > subtotal) desconto = subtotal;
  }

  // Usa a taxa global (que agora é atualizada corretamente pelo preencherCheckoutComAtivo)
  const taxa = isRetirada ? 0 : taxaEntregaAtual;

  // Cálculo final blindado
  const totalFinal = Math.max(0, subtotal + taxa - desconto);

  // 3. HTML do Resumo
  let itensHtml = carrinho
    .map(
      (item) => `
        <div class="confirm-item-row">
            <span>${item.quantity}x ${item.nome}</span>
            <span>R$ ${(item.preco * item.quantity)
              .toFixed(2)
              .replace(".", ",")}</span>
        </div>
        ${
          item.details && item.details.obs
            ? `<small style="color:#888; display:block; margin-top:-4px;">Obs: ${item.details.obs}</small>`
            : ""
        }
    `
    )
    .join("");

  let enderecoHtml = isRetirada
    ? `<p><strong>Tipo:</strong> Retirada no Balcão 🏃</p>`
    : `<p><strong>Entrega em:</strong> ${rua}, ${numero} - ${bairroNome}</p>
           ${complemento ? `<p><small>Comp: ${complemento}</small></p>` : ""}`;

  let html = `
        <div class="confirm-section">
            <h4>📦 Itens do Pedido</h4>
            ${itensHtml}
        </div>

        <div class="confirm-section confirm-info">
            <h4>📍 Dados da Entrega</h4>
            <p><strong>Cliente:</strong> ${nome} (${telefone})</p>
            ${enderecoHtml}
        </div>

        <div class="confirm-section confirm-info">
            <h4>💳 Pagamento</h4>
            <p><strong>Forma:</strong> ${metodoPagamento}</p>
        </div>

        <div class="confirm-section">
            <div class="confirm-item-row">
                <span>Subtotal:</span>
                <span>R$ ${subtotal.toFixed(2).replace(".", ",")}</span>
            </div>
            ${
              !isRetirada
                ? `
            <div class="confirm-item-row">
                <span>Entrega:</span>
                <span>R$ ${taxa.toFixed(2).replace(".", ",")}</span>
            </div>`
                : ""
            }
            
            ${
              desconto > 0
                ? `
            <div class="confirm-item-row" style="color: #2ecc71; font-weight: bold;">
                <span>Desconto:</span>
                <span>- R$ ${desconto.toFixed(2).replace(".", ",")}</span>
            </div>`
                : ""
            }
            
            <div class="confirm-total-row">
                <span>TOTAL:</span>
                <span>R$ ${totalFinal.toFixed(2).replace(".", ",")}</span>
            </div>
        </div>
    `;

  container.innerHTML = html;
  modal.classList.add("active");
  modal.style.display = "flex";
};

// Função que o botão "Confirmar" do modal chama
window.enviarPedidoFinal = function () {
  // Fecha o modal
  fecharModalConfirmacao();

  // Dispara o envio real (chama a função que já existe na API/Main logic)
  // Precisamos de um jeito de chamar o submitOrder original.
  // A maneira mais fácil é despachar um evento customizado ou chamar a função se ela estiver acessível.

  // Como o submitOrder coleta dados do form, basta chamar ele passando o form ou simulando o submit.
  // Mas para evitar recursividade, vamos chamar a lógica de envio diretamente.

  // AQUI ESTÁ O TRUQUE: Vamos chamar a função submitOrder importada do api.js
  // Mas precisamos dos dados. A submitOrder original pega do form.
  // Então vamos apenas disparar o evento submit no form mas com uma flag para "ignorar modal".

  const form = document.getElementById("contact-form");
  if (form) {
    // Marca o formulário como confirmado
    form.setAttribute("data-confirmed", "true");

    // Dispara o envio novamente (agora vai cair no IF correto do listener)
    form.requestSubmit();
  } else {
    console.error("Erro crítico: Formulário 'contact-form' não encontrado.");
    showToast("Erro ao enviar. Tente recarregar a página.", "error");
  }
};

// Função para exibir o erro crítico de cookies
export function showCookieError() {
  const modal = document.getElementById("modal-cookie-error");
  if (modal) {
    modal.style.display = "flex";
    // Toca um som de erro se quiser
    // const audio = new Audio("assets/error.mp3"); audio.play().catch(()=>{});
  } else {
    showToast(
      "ERRO CRÍTICO: Seu navegador está bloqueando cookies de terceiros. Por favor, habilite-os para fazer login.",
      "error"
    );
  }
}

// Exporta para o window para ser acessível globalmente se necessário
window.showCookieError = showCookieError;
let currentUserId = null;

// Substitua a função antiga por esta no final do main.js
function verificarUsuarioLogado() {
  // Usa a versão segura para pegar o ID real
  const realUser = getCurrentUserSecure();

  if (realUser && realUser.id) {
    currentUserId = realUser.id; // Atualiza global
    // ... mostra formulário de avaliação ...
    document
      .getElementById("form-avaliacao-wrapper")
      ?.classList.remove("hidden");
    document.getElementById("login-warning")?.classList.add("hidden");
  } else {
    currentUserId = null;
    // ... esconde formulário ...
    document.getElementById("form-avaliacao-wrapper")?.classList.add("hidden");
    document.getElementById("login-warning")?.classList.remove("hidden");
  }
}
// Lógica Visual das Estrelas do Input
function iniciarSistemaEstrelas() {
  const stars = document.querySelectorAll(".rating-input .star-icon");
  const ratingInput = document.getElementById("rating-value");
  if (!ratingInput) return; // Sai se não houver o campo de estrelas

  stars.forEach((star) => {
    star.addEventListener("click", function () {
      const valor = this.getAttribute("data-value");
      document.getElementById("rating-value").value = valor;

      // Pinta as estrelas
      stars.forEach((s) => {
        if (s.getAttribute("data-value") <= valor) {
          s.classList.add("star-filled");
        } else {
          s.classList.remove("star-filled");
        }
      });
    });
  });
}

async function carregarAvaliacoes() {
  const container = document.getElementById("lista-comentarios");
  const filtroElement = document.getElementById("filtro-stars");

  // Se não estivermos na página que tem as avaliações, sai da função silenciosamente
  if (!container || !filtroElement) return;

  const filtro = filtroElement.value;

  container.style.animation = "none";
  container.innerHTML =
    '<p class="loading-msg" style="color:white; width:100vw">Carregando...</p>';

  try {
    const res = await fetch(`/api/avaliar/listar?order=${filtro}`);
    const data = await res.json();

    // Salva na global para o modal usar (conforme solicitado anteriormente)
    window.reviewsCarregadas = data;

    container.innerHTML = "";
    if (data.length === 0) {
      container.innerHTML =
        '<p style="color:white; width:100vw">Nenhuma avaliação encontrada.</p>';
      return;
    }

    const createCardHTML = (review) => {
      const estrelasHTML =
        "★".repeat(review.stars) + "☆".repeat(5 - review.stars);
      return `
        <div class="review-card" onclick="prepararEAbrirModal(${review.id})" style="cursor: pointer;">
            <div class="review-header">
                <span class="review-author">${review.author}</span>
                <div class="review-stars">${estrelasHTML}</div>
            </div>
            <p class="review-text" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                ${review.coment}
            </p>
            <span class="review-date">${review.date}</span>
        </div>
      `;
    };

    const cardsHTML = data.map((review) => createCardHTML(review)).join("");
    container.innerHTML = cardsHTML + cardsHTML;
    const pixelsPorSegundo = 50;
    const primeiroCard = container.querySelector(".review-card");
    const gap = 25;
    const largura_item = primeiroCard ? primeiroCard.offsetWidth + gap : 325;

    let duration = (data.length * largura_item) / pixelsPorSegundo;
    if (duration < 10) duration = 15;
    container.style.animation = `scroll-left ${duration}s linear infinite`;
  } catch (error) {
    console.error("Erro ao buscar avaliações:", error);
  }
}

// NOVA FUNÇÃO: Faz a ponte entre o clique e o modal
window.prepararEAbrirModal = function (id) {
  // Use explicitamente window.reviewsCarregadas para evitar o conflito com a variável do topo
  const review = window.reviewsCarregadas
    ? window.reviewsCarregadas.find((r) => r.id === id)
    : null;

  if (review) {
    window.abrirModalDetalhes(review);
  } else {
    console.warn("Avaliação não encontrada na memória para o ID:", id);
  }
};

async function enviarAvaliacao() {
  const stars = document.getElementById("rating-value").value;
  const coment = document.getElementById("texto-avaliacao").value;
  const token = localStorage.getItem("access_token");

  if (stars == 0)
    return showToast("Por favor, selecione uma nota (estrelas).", "warning");
  if (!coment.trim()) return showToast("Escreva um comentário.", "warning");

  const res = await fetch("/api/avaliar", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ stars: stars, coment: coment }),
  });

  const data = await res.json();

  if (res.ok) {
    showToast("Avaliação enviada!", "success");
    document.getElementById("texto-avaliacao").value = "";
    document.getElementById("texto-avaliacao").value = "";

    // 2. RESETA AS ESTRELAS (Adicione isso aqui)
    document.getElementById("rating-value").value = "0"; // Zera o valor oculto

    // Remove a classe de brilho de todas as estrelas
    document.querySelectorAll(".rating-input .star-icon").forEach((star) => {
      star.classList.remove("star-filled");
    });
    carregarAvaliacoes(); // Recarrega a lista
  } else {
    showToast(data.error || "Erro ao enviar.", "error");
  }
}

async function deletarMinhaAvaliacao(id) {
  if (!confirm("Deseja realmente apagar seu comentário?")) return;

  const token = localStorage.getItem("access_token");
  const res = await fetch(`/api/avaliar/${id}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (res.ok) {
    carregarAvaliacoes();
  } else {
    showToast("Erro ao deletar.", "error");
  }
}
// --- SISTEMA DE MODAL DE AVALIAÇÃO ---

// =============================================================================
//  SISTEMA DE MODAL DE AVALIAÇÃO (MODO SEGURO)
// =============================================================================

let currentReviewId = null;

// 1. Funções do Modal
window.abrirModalDetalhes = function (review) {
  currentReviewId = review.id;
  const modal = document.getElementById("modal-review-overlay");
  if (!modal) return;

  document.getElementById("modal-current-id").value = review.id;
  document.getElementById("modal-author-name").innerText = review.author;
  document.getElementById("modal-review-date").innerText = review.date;
  document.getElementById("modal-review-text").innerText = review.coment;
  document.getElementById("modal-stars-display").innerText =
    "★".repeat(review.stars) + "☆".repeat(5 - review.stars);

  document.getElementById("edit-comment-input").value = review.coment;
  document.getElementById("edit-stars-input").value = review.stars;

  const ownerActions = document.getElementById("modal-owner-actions");
  cancelarEdicao();

  if (currentUserId && String(review.user_id) === String(currentUserId)) {
    ownerActions?.classList.remove("hidden");
  } else {
    ownerActions?.classList.add("hidden");
  }

  modal.classList.remove("hidden");
  modal.style.display = "flex";
};

window.fecharModalAvaliacao = function () {
  const modal = document.getElementById("modal-review-overlay");
  if (modal) modal.classList.add("hidden");
};

// 2. Lógica de Edição e Deleção no Modal
window.ativarEdicao = function () {
  document.getElementById("modal-review-text")?.classList.add("hidden");
  document.getElementById("modal-edit-area")?.classList.remove("hidden");
  document.getElementById("btn-edit-mode")?.classList.add("hidden");
  document.getElementById("btn-delete-modal")?.classList.add("hidden");
  document.getElementById("btn-save-edit")?.classList.remove("hidden");
  document.getElementById("btn-cancel-edit")?.classList.remove("hidden");
};

window.cancelarEdicao = function () {
  document.getElementById("modal-review-text")?.classList.remove("hidden");
  document.getElementById("modal-edit-area")?.classList.add("hidden");
  document.getElementById("btn-edit-mode")?.classList.remove("hidden");
  document.getElementById("btn-delete-modal")?.classList.remove("hidden");
  document.getElementById("btn-save-edit")?.classList.add("hidden");
  document.getElementById("btn-cancel-edit")?.classList.add("hidden");
};

window.salvarEdicao = async function () {
  const novoTexto = document.getElementById("edit-comment-input")?.value;
  const novasStars = document.getElementById("edit-stars-input")?.value;
  const token = localStorage.getItem("access_token");

  if (!novoTexto?.trim())
    return showToast("O comentário não pode ficar vazio.", "warning");

  try {
    const res = await fetch(`/api/avaliar/${currentReviewId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ coment: novoTexto, stars: novasStars }),
    });

    if (res.ok) {
      showToast("Avaliação atualizada!", "success");
      fecharModalAvaliacao();
      carregarAvaliacoes();
    } else {
      const data = await res.json();
      showToast(data.error || "Erro ao atualizar.", "error");
    }
  } catch (e) {
    showToast("Erro de conexão.", "error");
  }
};

window.deletarDoModal = async function () {
  if (confirm("Tem certeza que deseja apagar sua avaliação?")) {
    await deletarMinhaAvaliacao(currentReviewId);
    fecharModalAvaliacao();
  }
};

// 3. Listeners e Exportações Globais
const reviewOverlay = document.getElementById("modal-review-overlay");
if (reviewOverlay) {
  reviewOverlay.addEventListener("click", function (e) {
    if (e.target === this) fecharModalAvaliacao();
  });
}

function initCookieConsent() {
  const banner = document.getElementById("cookie-banner");
  const acceptBtn = document.getElementById("accept-cookies-btn");

  // Nome da chave no LocalStorage
  const STORAGE_KEY = "cegonha_cookie_consent";

  // 1. Verifica se já aceitou
  if (!localStorage.getItem(STORAGE_KEY)) {
    // Se não tem o registro, mostra o banner
    if (banner) banner.style.display = "flex";
  }

  // 2. Evento de Clique no OK
  if (acceptBtn) {
    acceptBtn.addEventListener("click", () => {
      // Salva a aceitação (funciona como um cookie persistente)
      localStorage.setItem(STORAGE_KEY, "true");

      // Adiciona animação de saída antes de esconder
      banner.style.transition = "transform 0.5s ease, opacity 0.5s ease";
      banner.style.transform = "translateY(100%)";
      banner.style.opacity = "0";

      // Remove do DOM após animação
      setTimeout(() => {
        banner.style.display = "none";
      }, 500);
    });
  }
}

// Garante que todas as funções importantes estão no objeto window
window.enviarAvaliacao = enviarAvaliacao;
window.deletarMinhaAvaliacao = deletarMinhaAvaliacao;
window.carregarAvaliacoes = carregarAvaliacoes;
window.iniciarSistemaEstrelas = iniciarSistemaEstrelas;
window.prepararEAbrirModal = prepararEAbrirModal;
