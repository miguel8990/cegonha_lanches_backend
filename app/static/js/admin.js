// site/js/admin.js
import {
  fetchAdminMenu,
  toggleAvailability,
  fetchAdminOrders,
  updateOrderStatus,
  fetchAdminConversations,
  fetchAdminUserHistory,
  sendAdminReply,
  uploadImage,
  createProduct,
  updateProduct,
  deleteProduct,
  fetchCoupons,
  createCoupon,
  deleteCoupon,
  fetchUsersList,
  fetchCloudGallery,
  deleteCloudImage,
  fetchNeighborhoodsAdmin,
  addNeighborhood,
  deleteNeighborhood,
  fetchSchedule,
  updateSchedule,
  fetchDashboardStats,
  fetchOrderDossier,
} from "./api.js";
import { getSession, clearSession, logout } from "./auth.js";
import { showToast } from "./utils.js";

// --- Variáveis de Estado ---
let chatUserIdAtivo = null;
let produtoEmEdicaoId = null; // null = criando, número = editando
let idParaDeletar = null; // Para o modal de segurança
let pedidosDoDia = [];
let chartInstance = null;

// =============================================================================
//  1. INICIALIZAÇÃO E SOCKETS
// =============================================================================

document.addEventListener("DOMContentLoaded", () => {
  // Verifica se é admin
  const { user } = getSession();
  if (!user.role || (user.role !== "admin" && user.role !== "super_admin")) {
    showToast("Acesso negado.", "error");
    window.location.href = "index.html";
    return;
  }

  // Carrega dados iniciais
  carregarPedidosAdmin();
  carregarMenuAdmin();
  carregarCozinha();

  // --- CONFIGURAÇÃO SOCKET.IO (REAL-TIME) ---
  // Detecta URL correta (Local ou Produção)
  const isLocalhost =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";
  const socketUrl = isLocalhost ? "http://localhost:5000" : ""; // Ajuste conforme seu api.js

  try {
    const socket = io(socketUrl);

    socket.on("connect", () => {
      console.log("🟢 Conectado ao sistema de pedidos em tempo real!");
      carregarPedidosAdmin();
      carregarCozinha();
      carregarListaConversas();
    });

    socket.on("novo_pedido", (pedido) => {
      console.log("🔔 Novo pedido recebido!", pedido);

      // Som de alerta
      const audio = new Audio("assets/notification.mp3");
      audio.play().catch(() => {});

      // Atualiza telas
      carregarCozinha();
      carregarPedidosAdmin();

      // Feedback visual (se o elemento toast existir no admin, senao alert simples)
      const toast = document.getElementById("toast-container");
      if (toast) {
        // Lógica de toast simples se houver container, senão console
        console.log("Toast: Novo Pedido Chegou");
      }
    });

    socket.on("chat_message", (msg) => {
      // 1. Toca som se for mensagem de cliente
      if (!msg.is_from_admin) {
        const audio = new Audio("assets/notification.mp3");
        audio.play().catch(() => {});
      }

      // 2. Se estiver com o chat desse usuário aberto, adiciona na tela
      if (chatUserIdAtivo === msg.user_id) {
        const container = document.getElementById("admin-chat-messages");
        if (container) {
          container.innerHTML += `<div class="msg ${
            msg.is_from_admin ? "msg-admin" : "msg-user"
          }">${msg.message}</div>`;
          container.scrollTop = container.scrollHeight;
        }
      } else {
        // Se não estiver aberto, mostra notificação
        if (!msg.is_from_admin)
          showToast(`Nova mensagem de Cliente #${msg.user_id}`, "info");
      }

      // 3. Atualiza a lista lateral para subir o usuário pro topo
      carregarListaConversas();
    });
  } catch (e) {
    console.warn("Socket.io não carregado ou falhou:", e);
  }

  carregarCozinha(); //tinha um setinterval aqui

  carregarListaConversas(); //tinha um setinterval aqui
});

// =============================================================================
//  GESTÃO DE PAINÉIS E NAVEGAÇÃO
// =============================================================================

function switchPanel(panelId) {
  document
    .querySelectorAll(".panel-section")
    .forEach((el) => el.classList.remove("active"));

  const target = document.getElementById(`panel-${panelId}`);
  if (target) target.classList.add("active");

  if (panelId === "kitchen") carregarCozinha();
  if (panelId === "delivery") carregarBairrosAdmin();
  if (panelId === "orders") carregarPedidosAdmin();

  // Atualiza menu lateral (visual)
  const btns = document.querySelectorAll(".sidebar-menu button");
  btns.forEach((btn) => btn.classList.remove("active"));

  // Tenta achar o botão que chamou a função (se via click)
  const activeBtn = Array.from(btns).find((btn) =>
    btn.getAttribute("onclick")?.includes(panelId)
  );
  if (activeBtn) activeBtn.classList.add("active");
}

async function adminLogout() {
  if (confirm("Tem certeza que deseja sair do Painel Administrativo?")) {
    // Apenas chame a função importada.
    // Ela já limpa a sessão, mostra o toast e redireciona após 1s.
    await logout();
  }
}
window.adminLogout = adminLogout;
// =============================================================================
//  ABA 1: PEDIDOS
// =============================================================================

// --- COZINHA (KDS) ---

async function carregarCozinha() {
  const pedidos = await fetchAdminOrders();
  pedidosDoDia = pedidos;

  const espera = pedidos.filter((p) => p.status === "Recebido");
  const preparo = pedidos.filter((p) => p.status === "Em Preparo");
  const entrega = pedidos.filter((p) => p.status === "Saiu para Entrega");

  renderizarFila("queue-waiting", espera, "espera");
  renderizarFila("queue-prep", preparo, "preparo");
  renderizarFila("queue-delivery", entrega, "entrega");
}

function renderizarFila(elementId, lista, tipo) {
  const container = document.getElementById(elementId);
  if (!container) return;

  if (lista.length === 0) {
    container.innerHTML = `<p style="text-align:center; color:#666; margin-top:20px; font-size:0.9rem;">Vazio</p>`;
    return;
  }

  container.innerHTML = lista
    .map((p) => {
      const hora = new Date(p.date_created).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });

      const totalFormatado = parseFloat(p.total_price || 0)
        .toFixed(2)
        .replace(".", ",");
      const classeAlerta = tipo === "espera" ? "card-alert" : "";

      let btnAcao = "";
      if (tipo === "espera") {
        btnAcao = `<button class="btn-primary full-width" onclick="window.moverParaPreparo(${p.id})">ACEITAR <i class="fa-solid fa-arrow-right"></i></button>`;
      } else if (tipo === "preparo") {
        btnAcao = `<button class="btn-primary full-width" style="background:#3498db; border-color:#3498db;" onclick="window.moverParaEntrega(${p.id})">SAIR P/ ENTREGA <i class="fa-solid fa-motorcycle"></i></button>`;
      } else if (tipo === "entrega") {
        btnAcao = `<button class="btn-primary full-width" style="background:#2ecc71; border-color:#2ecc71;" onclick="window.concluirPedidoDefinitivo(${p.id})">ENTREGUE ✅</button>`;
      }

      const itensHtml = p.items
        .map((i) => {
          let detalhesHtml = "";
          if (i.customizations_json) {
            try {
              const c = JSON.parse(i.customizations_json);
              const extras = [
                ...(c.carnes || []),
                ...(c.adicionais || []),
                ...(c.acompanhamentos || []),
                ...(c.bebidas || []),
              ];
              if (extras.length > 0) {
                detalhesHtml += `<div style="font-size:0.85rem; color:#aaa; margin-left:10px; margin-top:2px;">+ ${extras.join(
                  ", "
                )}</div>`;
              }
              if (c.obs) {
                detalhesHtml += `<div class="k-obs" style="font-size:0.85rem; color:#f1c40f; margin-left:10px; margin-top:2px;">⚠️ ${c.obs}</div>`;
              }
            } catch (e) {}
          }
          return `
            <div class="k-item" style="border-bottom:1px solid #333; padding:8px 0;">
                <div style="font-size:1rem;"><strong>${i.quantity}x ${i.product.name}</strong></div>
                ${detalhesHtml}
            </div>`;
        })
        .join("");

      const enderecoHtml = p.street
        ? `📍 ${p.street}, ${p.number} - ${p.neighborhood} ${
            p.complement ? `(${p.complement})` : ""
          }`
        : `🏃 Retirada no Local`;

      const pagamentoHtml =
        p.payment_method === "cash" ? "Dinheiro" : p.payment_method;

      return `
            <div class="kitchen-card ${classeAlerta}" style="display:flex; flex-direction:column; gap:10px;">
                <div style="display:flex; justify-content:space-between; border-bottom:1px solid #444; padding-bottom:5px;">
                    <span style="font-size:1rem; font-weight:bold;">#${
                      p.id
                    } - ${p.customer_name.split(" ")[0]}</span>
                    <span style="color:#aaa; font-size:0.9rem;">${hora}</span>
                </div>
                <div>${itensHtml}</div> 
                <div style="background:#222; padding:8px; border-radius:5px; font-size:0.85rem; color:#ccc; margin-top:auto;">
                    <div style="margin-bottom:5px;">${enderecoHtml}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #444; padding-top:5px;">
                        <span>💳 ${pagamentoHtml}</span>
                        <span style="color:var(--color-gold); font-size:1rem; font-weight:bold;">R$ ${totalFormatado}</span>
                    </div>
                </div>
                <div style="display:flex; gap:5px; margin-top:5px;">
                    ${btnAcao}
                    <button class="btn-small btn-cancel" onclick="window.imprimirComanda(${
                      p.id
                    })" title="Imprimir" style="padding: 0 15px;">
                        <i class="fa-solid fa-print"></i>
                    </button>
                </div>
            </div>
        `;
    })
    .join("");
}

async function moverParaPreparo(id) {
  await updateOrderStatus(id, "Em Preparo");
  carregarCozinha();
}

async function moverParaEntrega(id) {
  await updateOrderStatus(id, "Saiu para Entrega");
  carregarCozinha();
}

async function concluirPedidoDefinitivo(id) {
  if (confirm("Confirmar que o pedido foi entregue e pago?")) {
    await updateOrderStatus(id, "Concluído");
    carregarCozinha();
  }
}

// --- HISTÓRICO DE PEDIDOS ---

async function carregarPedidosAdmin(filtrosOpcionais = null) {
  const container = document.getElementById("admin-orders-list");
  const btn = document.querySelector("#panel-orders .btn-outline");

  if (btn) btn.innerHTML = '<i class="fa-solid fa-rotate fa-spin"></i> ...';

  let filtrosFinais = filtrosOpcionais;
  if (!filtrosFinais) {
    const hoje = new Date().toISOString().split("T")[0];
    filtrosFinais = { start_date: hoje, end_date: hoje };
  }

  const pedidos = await fetchAdminOrders(filtrosFinais);
  pedidosDoDia = pedidos;

  if (!container) return;

  container.innerHTML = pedidos.length
    ? pedidos.map((p) => renderOrderCard(p)).join("")
    : '<div style="text-align:center; padding:20px; color:#666; grid-column: 1 / -1;">Nenhum pedido encontrado com estes filtros.</div>';

  if (btn) btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Atualizar';
}

function renderOrderCard(p) {
  const time = new Date(p.date_created).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  let botoes = "";
  if (p.status !== "Concluído" && p.status !== "Cancelado")
    botoes += ` <button class="btn-small btn-cancel" onclick="window.mudarStatus(${p.id}, 'Cancelado')">Cancelar ❌</button>`;

  const totalNum = parseFloat(p.total_price || 0);
  const totalFormatado = totalNum.toFixed(2).replace(".", ",");

  const itemsHtml = p.items
    .map((i) => `<div><strong>${i.quantity}x ${i.product.name}</strong></div>`)
    .join("");

  return `
    <div class="admin-order-card status-${p.status.replace(/ /g, ".")}">
        <div class="card-header">
            <span class="card-user">#${p.id} - ${
    p.customer_name || "Cliente"
  }</span>
            <span class="card-time">${time}</span>
        </div>
        <div class="card-items">${itemsHtml}</div>
        <div style="font-size:0.85rem; margin:10px 0;">
            📍 ${p.street}, ${p.number}<br>
            💳 <strong>${p.payment_method}</strong><br>
            <span style="color:gold">R$ ${totalFormatado}</span>
        </div>
        <div class="card-actions">
            <button class="btn-small" onclick="window.imprimirComanda(${
              p.id
            })" style="background:#555; color:white; border:none; margin-right:5px;" title="Imprimir">
                <i class="fa-solid fa-print"></i>
            </button>
            ${botoes}
            <button class="btn-small" onclick="window.abrirDossie(${
              p.id
            })" style="background:#444; color:#aaa; border:none; margin-right:5px;" title="Dossiê">
                <i class="fa-solid fa-magnifying-glass"></i>
            </button>
        </div>
        <div style="text-align:right; font-size:0.8rem; color:#666; margin-top:5px;">${
          p.status
        }</div>
    </div>`;
}

async function mudarStatus(id, novo) {
  if (confirm(`Mudar status do pedido #${id} para '${novo}'?`)) {
    await updateOrderStatus(id, novo);
    carregarPedidosAdmin();
  }
}

// =============================================================================
//  ABA 2: CARDÁPIO
// =============================================================================

async function carregarMenuAdmin() {
  const tbody = document.getElementById("admin-menu-list");
  if (!tbody) return;

  const produtos = await fetchAdminMenu();

  if (produtos.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4">Cardápio vazio.</td></tr>';
    return;
  }

  tbody.innerHTML = produtos
    .map((p) => {
      const precoNum = parseFloat(p.price || 0);
      return `
        <tr>
            <td>${p.name}</td>
            <td>R$ ${precoNum.toFixed(2).replace(".", ",")}</td>
            <td style="text-align:center;">
                <i class="toggle-switch fa-solid ${
                  p.is_available ? "fa-toggle-on on" : "fa-toggle-off off"
                }" 
                   onclick="window.toggleProd(${p.id})" 
                   style="font-size:1.5rem; cursor:pointer;" title="Pausar/Ativar"></i>
            </td>
            <td>
                <div style="display:flex; gap:5px; justify-content:center;">
                    <button class="btn-small" style="background:#3498db; color:white; border:none;" 
                            onclick="window.editarProduto(${
                              p.id
                            })"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn-small" style="background:#e74c3c; color:white; border:none;" 
                            onclick="window.deletarProduto(${
                              p.id
                            })"><i class="fa-solid fa-trash"></i></button>
                </div>
            </td>
        </tr>`;
    })
    .join("");
}

async function toggleProd(id) {
  await toggleAvailability(id);
  carregarMenuAdmin();
}

// --- MODAL PRODUTO ---

function openProductModal() {
  produtoEmEdicaoId = null;
  document.getElementById("form-add-product").reset();
  document.querySelector("#modal-product-admin h3").innerText = "Novo Produto";
  document.querySelector('#form-add-product button[type="submit"]').innerText =
    "Cadastrar Produto";

  document.getElementById("preview-img").style.display = "none";
  document.getElementById("preview-icon").style.display = "block";
  document.getElementById("prod-image-url").value = "";

  const lbl = document.getElementById("btn-upload-pc");
  if (lbl) {
    lbl.innerHTML =
      '<i class="fa-solid fa-cloud-arrow-up"></i> <span>Upload PC</span>';
    lbl.style.color = "";
    lbl.style.borderColor = "";
  }

  document.getElementById("details-container").innerHTML = "";
  addDetailRow();
  addDetailRow();
  document.getElementById("modal-product-admin").style.display = "flex";
}

async function editarProduto(id) {
  const produtos = await fetchAdminMenu();
  const produto = produtos.find((p) => p.id === id);
  if (!produto) return;

  produtoEmEdicaoId = id;
  document.querySelector("#modal-product-admin h3").innerText =
    "Editar Produto";
  document.querySelector('#form-add-product button[type="submit"]').innerText =
    "Salvar Alterações";

  document.getElementById("prod-name").value = produto.name;
  document.getElementById("prod-price").value = parseFloat(produto.price || 0);
  document.getElementById("prod-category").value = produto.category || "Lanche";
  document.getElementById("prod-desc").value = produto.description || "";
  document.getElementById("prod-image-url").value = produto.image_url || "";

  if (document.getElementById("prod-stock")) {
    document.getElementById("prod-stock").value =
      produto.stock_quantity !== null && produto.stock_quantity !== undefined
        ? produto.stock_quantity
        : "";
  }

  if (produto.image_url) {
    const img = document.getElementById("preview-img");
    img.src = produto.image_url;
    img.style.display = "block";
    document.getElementById("preview-icon").style.display = "none";
  }

  const container = document.getElementById("details-container");
  container.innerHTML = "";

  let details = {};
  try {
    details =
      typeof produto.details_json === "string"
        ? JSON.parse(produto.details_json)
        : produto.details || {};
  } catch (e) {}

  let temDetalhes = false;
  ["carnes", "adicionais", "acompanhamentos", "bebidas"].forEach((key) => {
    if (details[key]) {
      details[key].forEach((item) => {
        const priceNum = parseFloat(item.price || 0);
        const val = priceNum > 0 ? `${item.nome} - ${priceNum}` : item.nome;
        addDetailRow(key, val);
        temDetalhes = true;
      });
    }
  });

  if (!temDetalhes) addDetailRow();
  document.getElementById("modal-product-admin").style.display = "flex";
}

function closeProductModal() {
  document.getElementById("modal-product-admin").style.display = "none";
}

function addDetailRow(key = "adicionais", value = "", isManual = false) {
  const container = document.getElementById("details-container");
  const div = document.createElement("div");
  div.className = "detail-row";

  div.innerHTML = `
        <select class="detail-key">
            <option value="adicionais" ${
              key === "adicionais" ? "selected" : ""
            }>Adicional</option>
            <option value="acompanhamentos" ${
              key === "acompanhamentos" ? "selected" : ""
            }>Acomp.</option>
            <option value="bebidas" ${
              key === "bebidas" ? "selected" : ""
            }>Bebida</option>
            <option value="carnes" ${
              key === "carnes" ? "selected" : ""
            }>Carne</option>
            <option value="opcoes" ${
              key === "opcoes" ? "selected" : ""
            }>Opção</option>
        </select>
        
        <button type="button" class="btn-remove-detail" onclick="window.removeDetailRow(this)" title="Remover">
            &times;
        </button>
        
        <input type="text" class="detail-val" value="${value}" placeholder="Nome - Preço (Ex: Bacon - 3.00)">
    `;

  container.appendChild(div);

  // A MÁGICA: Só mostra o toast se for uma ação manual do usuário
  if (isManual) {
    showToast("+1 Item adicionado", "success");

    // Opcional: Foca no input novo para facilitar a digitação
    setTimeout(() => {
      const inputs = container.querySelectorAll(".detail-val");
      inputs[inputs.length - 1].focus();
    }, 100);
  }
}

function removeDetailRow(btn) {
  btn.parentElement.remove();
}

// Listeners de Formulário de Produto
const fileInput = document.getElementById("prod-file");
if (fileInput) {
  fileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // ... Lógica de upload mantida ...
    const lbl = document.getElementById("btn-upload-pc");
    lbl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Enviando...';

    try {
      const url = await uploadImage(file);
      if (url) {
        document.getElementById("prod-image-url").value = url;
        const img = document.getElementById("preview-img");
        img.src = url;
        img.style.display = "block";
        document.getElementById("preview-icon").style.display = "none";
        lbl.innerHTML = "Foto OK ✅";
      }
    } catch (err) {
      showToast("Erro no upload", "error");
      lbl.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Upload PC';
    }
  });
}

const formProd = document.getElementById("form-add-product");
if (formProd) {
  formProd.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = formProd.querySelector('button[type="submit"]');
    btn.innerText = "Salvando...";
    btn.disabled = true;
    const stockVal = document.getElementById("prod-stock").value;

    try {
      const data = {
        name: document.getElementById("prod-name").value,
        price: parseFloat(document.getElementById("prod-price").value),
        category: document.getElementById("prod-category").value,
        description: document.getElementById("prod-desc").value,
        image_url: document.getElementById("prod-image-url").value,
        stock_quantity: stockVal === "" ? null : parseInt(stockVal),
        details: {
          carnes: [],
          adicionais: [],
          acompanhamentos: [],
          bebidas: [],
        },
      };

      document.querySelectorAll("#details-container > div").forEach((row) => {
        const key = row.querySelector(".detail-key").value;
        const val = row.querySelector(".detail-val").value.trim();
        if (val) {
          let nomeItem = val;
          let precoItem = 0.0;
          if (val.includes("-")) {
            const partes = val.split("-");
            nomeItem = partes[0].trim();
            precoItem = parseFloat(partes[1].replace(",", ".").trim()) || 0;
          }
          data.details[key].push({ nome: nomeItem, price: precoItem });
        }
      });

      let ok = false;
      if (produtoEmEdicaoId) ok = await updateProduct(produtoEmEdicaoId, data);
      else ok = await createProduct(data);

      if (ok) {
        showToast(
          produtoEmEdicaoId ? "Produto atualizado!" : "Produto criado!",
          "success"
        );
        closeProductModal();
        carregarMenuAdmin();
      } else throw new Error("Erro no servidor");
    } catch (err) {
      showToast("Erro ao salvar: " + err.message, "error");
    } finally {
      btn.innerText = produtoEmEdicaoId
        ? "Salvar Alterações"
        : "Cadastrar Produto";
      btn.disabled = false;
    }
  });
}

// --- SEGURANÇA ---

function deletarProduto(id) {
  idParaDeletar = id;
  const modal = document.getElementById("modal-security");
  const input = document.getElementById("security-pass");
  input.value = "";
  modal.style.display = "flex";
  setTimeout(() => input.focus(), 100);
}

function closeSecurityModal() {
  document.getElementById("modal-security").style.display = "none";
  idParaDeletar = null;
}

async function executarDelecao() {
  const input = document.getElementById("security-pass");
  const btn = document.querySelector("#modal-security .btn-primary");
  const senha = input.value;

  if (!senha) return showToast("Digite a senha mestra.", "warning");
  if (!idParaDeletar) return;

  btn.innerHTML = "Verificando...";
  btn.disabled = true;

  const result = await deleteProduct(idParaDeletar, senha);

  if (result === true) {
    showToast("Produto excluído!", "success");
    closeSecurityModal();
    carregarMenuAdmin();
  } else {
    showToast(result.error || "Senha incorreta ou erro.", "error");
    input.value = "";
    input.focus();
  }
  btn.innerHTML = '<i class="fa-solid fa-trash"></i> Excluir Agora';
  btn.disabled = false;
}

document.getElementById("security-pass")?.addEventListener("keypress", (e) => {
  if (e.key === "Enter") executarDelecao();
});

// =============================================================================
//  ABA 3: CHAT
// =============================================================================

async function carregarListaConversas() {
  const lista = await fetchAdminConversations();
  const container = document.getElementById("chat-users-list");
  if (!container) return;

  if (lista.length === 0) {
    container.innerHTML =
      '<p style="padding:20px; color:#666">Nenhuma conversa.</p>';
    return;
  }

  container.innerHTML = lista
    .map(
      (u) => `
        <div class="chat-user-item ${
          chatUserIdAtivo === u.user_id ? "active" : ""
        }" 
             onclick="window.selecionarChat(${u.user_id}, '${u.user_name}')">
            <div class="user-avatar-small">${u.user_name[0].toUpperCase()}</div>
            <div style="flex:1">
                <div>${u.user_name}</div>
                <small style="color:#888">${new Date(u.last_interaction)
                  .toLocaleTimeString()
                  .slice(0, 5)}</small>
            </div>
        </div>
    `
    )
    .join("");
}

function selecionarChat(id, nome) {
  chatUserIdAtivo = id;
  const inputArea = document.getElementById("admin-chat-input-area");
  if (inputArea) inputArea.style.display = "flex";
  carregarChatAtivo(id);
  carregarListaConversas();
}

async function carregarChatAtivo(uid) {
  const msgs = await fetchAdminUserHistory(uid);
  const container = document.getElementById("admin-chat-messages");
  if (!container) return;

  container.innerHTML = msgs
    .map(
      (m) =>
        `<div class="msg ${m.is_from_admin ? "msg-admin" : "msg-user"}">${
          m.message
        }</div>`
    )
    .join("");
  container.scrollTop = container.scrollHeight;
}

async function enviarRespostaAdmin() {
  const inp = document.getElementById("admin-chat-input");
  const txt = inp.value.trim();
  if (!txt || !chatUserIdAtivo) return;

  if (await sendAdminReply(chatUserIdAtivo, txt)) {
    inp.value = "";
    carregarChatAtivo(chatUserIdAtivo);
  } else {
    showToast("Erro ao enviar.", "error");
  }
}

function handleAdminChatKey(e) {
  if (e.key === "Enter") enviarRespostaAdmin();
}

// =============================================================================
//  ABA 4: CONFIGURAÇÕES
// =============================================================================

// 1. Unifica a troca de abas de configuração
function switchConfigTab(tabName) {
  // Gerencia o estado visual dos botões
  document.querySelectorAll(".config-tab-btn").forEach((btn) => {
    btn.classList.remove("active");
    if (btn.getAttribute("onclick").includes(`'${tabName}'`)) {
      btn.classList.add("active");
    }
  });

  // Esconde todos os subpainéis
  document.querySelectorAll(".config-subpanel").forEach((el) => {
    el.style.display = "none";
  });

  // Mostra o painel correto (usando o prefixo config- definido no HTML)
  const target = document.getElementById(`config-${tabName}`);
  if (target) {
    target.style.display = "block";
  }

  // Carrega os dados automaticamente
  if (tabName === "coupons") carregarCuponsAdmin();
  if (tabName === "users") carregarUsuariosAdmin();
  if (tabName === "schedule") carregarHorariosAdmin();
  if (tabName === "reviews") carregarAvaliacoesAdmin();
}

async function carregarCuponsAdmin() {
  const container = document.getElementById("coupons-list");
  if (!container) return;
  const lista = await fetchCoupons();

  if (lista.length === 0) {
    container.innerHTML = '<p style="color:#666">Nenhum cupom ativo.</p>';
    return;
  }

  container.innerHTML = lista
    .map(
      (c) => `
        <div class="coupon-card">
            <div class="coupon-code">${c.code}</div>
            <div class="coupon-info">
                ${
                  c.discount_percent > 0
                    ? c.discount_percent + "% OFF"
                    : "R$ " + parseFloat(c.discount_fixed).toFixed(2) + " OFF"
                }
            </div>
            <div class="coupon-info">Min: R$ ${parseFloat(
              c.min_purchase
            ).toFixed(2)}</div>
            <div class="coupon-info">Usos: ${c.used_count} / ${
        c.usage_limit || "∞"
      }</div>
            
            <button class="btn-small btn-cancel" onclick="window.deletarCupom(${
              c.id
            })" 
                style="position:absolute; top:10px; right:10px; border:none; background:transparent; color:#e74c3c;">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `
    )
    .join("");
}

function toggleNewCouponForm() {
  const form = document.getElementById("form-new-coupon");
  if (form)
    form.style.display = form.style.display === "none" ? "block" : "none";
}

async function deletarCupom(id) {
  if (confirm("Apagar este cupom permanentemente?")) {
    await deleteCoupon(id);
    carregarCuponsAdmin();
  }
}

const formCupom = document.getElementById("form-new-coupon");
if (formCupom) {
  formCupom.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {
      code: document.getElementById("cupom-code").value.trim(),
      discount_percent:
        parseInt(document.getElementById("cupom-percent").value) || 0,
      discount_fixed:
        parseFloat(document.getElementById("cupom-fixed").value) || 0,
      min_purchase: parseFloat(document.getElementById("cupom-min").value) || 0,
      usage_limit:
        parseInt(document.getElementById("cupom-limit").value) || null,
    };

    if (await createCoupon(data)) {
      showToast("Cupom criado!", "success");
      formCupom.reset();
      formCupom.style.display = "none";
      carregarCuponsAdmin();
    } else showToast("Erro (código já existe?)", "error");
  });
}

async function carregarUsuariosAdmin() {
  const tbody = document.getElementById("users-list-body");
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="4">Carregando...</td></tr>';

  const lista = await fetchUsersList();

  if (lista.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="4">Nenhum usuário encontrado.</td></tr>';
    return;
  }
  lista.sort((a, b) => b.orders_count - a.orders_count);
  tbody.innerHTML = lista
    .map((u) => {
      // Formatação simples do WhatsApp para link clicável
      const zapClean = u.whatsapp ? u.whatsapp.replace(/\D/g, "") : "";
      const zapDisplay = u.whatsapp
        ? `<a href="https://wa.me/55${zapClean}" target="_blank" style="color:#2ecc71; text-decoration:none;">
             <i class="fa-brands fa-whatsapp"></i> ${u.whatsapp}
           </a>`
        : "-";

      // Badge Dourada para contagem (Estilo visual)
      return `
        <tr>
            <td><strong>${u.name}</strong></td>
            <td>${zapDisplay}</td>
            <td>
                <span style="background:#333; color:#f1c40f; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:0.9rem;">
                    ${u.orders_count} pedidos
                </span>
            </td>
        </tr>`;
    })
    .join("");
}

// GALERIA CLOUDINARY

async function abrirGaleriaNuvem() {
  const modal = document.getElementById("modal-cloud-gallery");
  const container = document.getElementById("cloud-grid");
  modal.style.display = "flex";
  container.innerHTML =
    '<p style="color:#ccc"><i class="fa-solid fa-spinner fa-spin"></i> Carregando nuvem...</p>';

  try {
    const imagens = await fetchCloudGallery();
    if (imagens.length === 0) {
      container.innerHTML =
        '<p style="color:#ccc">Nenhuma imagem encontrada na nuvem.</p>';
      return;
    }
    container.innerHTML = imagens
      .map((img) => {
        const nomeExibicao = img.name.split("/").pop();
        return `
            <div class="gallery-item" onclick="window.selecionarImagemCloud('${img.url}')" title="${img.name}">
                <button class="btn-delete-img" onclick="window.apagarImagemCloud(event, '${img.name}')" title="Apagar permanentemente">
                    <i class="fa-solid fa-trash"></i>
                </button>
                <img src="${img.url}" loading="lazy">
                <div class="gallery-name">${nomeExibicao}</div>
            </div>`;
      })
      .join("");
  } catch (e) {
    container.innerHTML =
      '<p style="color:#e74c3c">Erro ao carregar galeria. Verifique a configuração.</p>';
  }
}

function fecharGaleriaNuvem() {
  document.getElementById("modal-cloud-gallery").style.display = "none";
}

function selecionarImagemCloud(url) {
  document.getElementById("prod-image-url").value = url;
  const img = document.getElementById("preview-img");
  img.src = url;
  img.style.display = "block";
  document.getElementById("preview-icon").style.display = "none";
  fecharGaleriaNuvem();
}

async function apagarImagemCloud(event, publicId) {
  event.stopPropagation();
  if (
    !confirm(
      "Tem certeza? Essa imagem será apagada do servidor permanentemente."
    )
  )
    return;
  const btn = event.currentTarget;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
  const sucesso = await deleteCloudImage(publicId);
  if (sucesso) await abrirGaleriaNuvem();
  else {
    showToast("Erro ao apagar. Verifique se tem permissão.", "error");
    btn.innerHTML = '<i class="fa-solid fa-trash"></i>';
  }
}

// TAXAS DE ENTREGA

async function carregarBairrosAdmin() {
  const lista = await fetchNeighborhoodsAdmin();
  const container = document.getElementById("delivery-list");
  if (!container) return;

  container.innerHTML = lista
    .map((b) => {
      const taxaFloat = parseFloat(b.price || 0);
      return `
        <div class="coupon-card" style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <strong style="color:var(--color-gold); font-size:1.1rem;">${
                  b.name
                }</strong>
                <div style="color:#ccc;">Taxa: R$ ${taxaFloat
                  .toFixed(2)
                  .replace(".", ",")}</div>
            </div>
            <button 
            style="width: 30px; height: 30px; background-color: #e74c3c; color: white; border: none; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px rgba(0,0,0,0.2); transition: transform 0.2s;"
            onmouseover="this.style.transform='scale(1.1)'"
            onmouseout="this.style.transform='scale(1)'"
            onclick="window.apagarBairro(${b.id})">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>`;
    })
    .join("");
}

async function adicionarBairro() {
  const nome = document.getElementById("new-bairro-name").value;
  const preco = document.getElementById("new-bairro-price").value;
  if (!nome || !preco) return showToast("Preencha nome e valor", "warning");

  if (await addNeighborhood({ name: nome, price: preco })) {
    document.getElementById("new-bairro-name").value = "";
    document.getElementById("new-bairro-price").value = "";
    carregarBairrosAdmin();
  } else showToast("Erro ao salvar (Bairro já existe?)", "error");
}

async function apagarBairro(id) {
  if (confirm("Remover este bairro?")) {
    await deleteNeighborhood(id);
    carregarBairrosAdmin();
  }
}

// IMPRESSÃO

function imprimirComanda(id) {
  const pedido = pedidosDoDia.find((p) => p.id === id);
  if (!pedido)
    return showToast(
      "Erro: Pedido não encontrado na memória. Atualize a página.",
      "error"
    );

  const dataObj = new Date(pedido.date_created);
  const dataFormatada =
    dataObj.toLocaleDateString("pt-BR") +
    " " +
    dataObj.toLocaleTimeString("pt-BR").slice(0, 5);

  let itensHtml = "";
  pedido.items.forEach((item) => {
    let detalhes = "";
    if (item.customizations_json) {
      try {
        const cust = JSON.parse(item.customizations_json);
        const lista = [
          ...(cust.carnes || []),
          ...(cust.adicionais || []),
          ...(cust.acompanhamentos || []),
          ...(cust.bebidas || []),
        ];
        if (lista.length > 0)
          detalhes = `<div style="font-size:10px; margin-left:10px; color:#444;">+ ${lista.join(
            ", "
          )}</div>`;
        if (cust.obs)
          detalhes += `<div style="font-size:10px; margin-left:10px; font-weight:bold;">OBS: ${cust.obs}</div>`;
      } catch (e) {}
    }

    const priceAtTime = parseFloat(item.price_at_time || 0);
    const subtotal = priceAtTime * item.quantity;

    itensHtml += `
      <div style="margin-bottom:5px; border-bottom:1px dashed #ccc; padding-bottom:2px;">
        <div style="display:flex; justify-content:space-between; font-weight:bold;">
            <span>${item.quantity}x ${item.product.name}</span>
            <span>R$ ${subtotal.toFixed(2)}</span>
        </div>
        ${detalhes}
      </div>`;
  });

  const deliveryFee = parseFloat(pedido.delivery_fee || 0);
  const totalPrice = parseFloat(pedido.total_price || 0);

  const conteudoJanela = `
    <html>
      <head>
        <title>Pedido #${pedido.id}</title>
        <style>
          @page { margin: 0; }
          body { font-family: 'Courier New', monospace; font-size: 12px; margin: 0; padding: 10px; width: 300px; color: #000; }
          .header { text-align: center; margin-bottom: 10px; border-bottom: 2px solid #000; padding-bottom: 5px; }
          .section { margin-bottom: 10px; border-bottom: 1px solid #000; padding-bottom: 5px; }
          .bold { font-weight: bold; }
          .big { font-size: 14px; }
          .center { text-align: center; }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="big bold">CEGONHA LANCHES</div>
          <div>Itapagipe - MG</div>
          <div style="margin-top:5px;">PEDIDO #${pedido.id}</div>
          <div>${dataFormatada}</div>
        </div>
        <div class="section">
          <div class="bold">CLIENTE:</div>
          <div>${pedido.customer_name || "Consumidor"}</div>
          <div>Tel: ${pedido.customer_phone || "-"}</div>
          <div style="margin-top:5px;" class="bold">ENTREGA:</div>
          <div>${pedido.street}, ${pedido.number}</div>
          <div>${pedido.neighborhood} ${
    pedido.complement ? "- " + pedido.complement : ""
  }</div>
        </div>
        <div class="section">
          <div class="bold" style="margin-bottom:5px;">ITENS:</div>
          ${itensHtml}
        </div>
        <div class="section">
          <div style="display:flex; justify-content:space-between;">
             <span>Taxa Entrega:</span>
             <span>R$ ${deliveryFee.toFixed(2)}</span>
          </div>
          <div style="display:flex; justify-content:space-between; font-size:16px; font-weight:bold; margin-top:5px;">
             <span>TOTAL:</span>
             <span>R$ ${totalPrice.toFixed(2)}</span>
          </div>
        </div>
        <div class="center">
          <div>Pagamento: <strong>${pedido.payment_method}</strong></div>
          <div style="margin-top:10px; font-size:10px;">Sistema Cegonha Lanches</div>
        </div>
      </body>
    </html>`;

  const janela = window.open("", "_blank", "width=350,height=600");
  janela.document.write(conteudoJanela);
  janela.document.close();
  setTimeout(() => janela.print(), 500);
}

// HORÁRIOS

const diasSemana = [
  "Domingo",
  "Segunda",
  "Terça",
  "Quarta",
  "Quinta",
  "Sexta",
  "Sábado",
];

async function carregarHorariosAdmin() {
  const lista = await fetchSchedule();
  const tbody = document.getElementById("schedule-list-body");
  if (!tbody) return;

  tbody.innerHTML = lista
    .map(
      (d) => `
        <tr data-day="${d.day_of_week}">
            <td><strong>${diasSemana[d.day_of_week]}</strong></td>
            <td><input type="time" class="inp-time open" value="${
              d.open_time
            }" style="background:#111; border:1px solid #444; color:white; padding:5px; border-radius:4px;"></td>
            <td><input type="time" class="inp-time close" value="${
              d.close_time
            }" style="background:#111; border:1px solid #444; color:white; padding:5px; border-radius:4px;"></td>
            <td>
                <label class="checkbox-container" style="margin:0;">
                    <input type="checkbox" class="inp-closed" ${
                      d.is_closed ? "checked" : ""
                    }>
                    <span class="checkmark"></span>
                </label>
            </td>
        </tr>`
    )
    .join("");
}

async function salvarHorarios() {
  const linhas = document.querySelectorAll("#schedule-list-body tr");
  const payload = [];
  linhas.forEach((tr) => {
    payload.push({
      day_of_week: parseInt(tr.dataset.day),
      open_time: tr.querySelector(".open").value,
      close_time: tr.querySelector(".close").value,
      is_closed: tr.querySelector(".inp-closed").checked,
    });
  });

  if (await updateSchedule(payload))
    showToast("Horários atualizados!", "success");
  else showToast("Erro ao salvar.", "error");
}

// DASHBOARD

async function carregarDashboard(filtros = {}) {
  const btn = document.querySelector("#panel-reports .btn-outline");
  if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

  const dados = await fetchDashboardStats(filtros);
  if (btn) btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Atualizar';

  if (!dados) return;

  const totalPeriodo = parseFloat(dados.total_periodo || 0);
  document.getElementById(
    "stat-faturamento"
  ).innerText = `R$ ${totalPeriodo.toFixed(2)}`;
  document.getElementById("stat-qtd").innerText = dados.qtd_pedidos;
  document.getElementById(
    "report-period-label"
  ).innerText = `Período: ${dados.periodo_info}`;

  const ctx = document.getElementById("salesChart").getContext("2d");
  if (chartInstance) chartInstance.destroy();

  chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: dados.grafico.labels,
      datasets: [
        {
          label: "Vendas (R$)",
          data: dados.grafico.data,
          backgroundColor: "rgba(242, 201, 76, 0.2)",
          borderColor: "#f2c94c",
          borderWidth: 2,
          fill: true,
          tension: 0.4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "white" } } },
      scales: {
        y: {
          ticks: { color: "#ccc", callback: (v) => "R$ " + v },
          grid: { color: "#333" },
        },
        x: { ticks: { color: "#ccc" }, grid: { display: false } },
      },
    },
  });
}

// DOSSIE

async function abrirDossie(id) {
  const dossie = await fetchOrderDossier(id);
  if (!dossie) return showToast("Erro ao carregar dossiê.", "error");

  const container = document.getElementById("dossier-body");
  const d = dossie;

  const itensLegiveis = d.items
    .map(
      (i) =>
        ` - ${i.quantity}x ${i.product.name} (R$ ${parseFloat(
          i.price_at_time
        ).toFixed(2)})`
    )
    .join("<br>");

  const totalDossie = parseFloat(d.total_price || 0).toFixed(2);
  const taxaDossie = parseFloat(d.delivery_fee || 0).toFixed(2);

  container.innerHTML = `
        <div style="background:#222; padding:10px; border-radius:5px; margin-bottom:10px;">
            <strong>🆔 PEDIDO:</strong> #${d.id}<br>
            <strong>📅 DATA:</strong> ${new Date(
              d.date_created
            ).toLocaleString()}<br>
            <strong>👤 CLIENTE:</strong> ${d.customer_name} (${
    d.customer_phone
  })<br>
            <strong>🚦 STATUS ATUAL:</strong> ${d.status}
        </div>
        <div style="background:#222; padding:10px; border-radius:5px; margin-bottom:10px;">
            <strong>💳 PAGAMENTO:</strong><br>
            Método: ${d.payment_method}<br>
            Status: <span style="color:${
              d.payment_status === "approved" ? "#2ecc71" : "#e74c3c"
            }">${d.payment_status}</span><br>
            Total Pago: R$ ${totalDossie}
        </div>
        <div style="background:#222; padding:10px; border-radius:5px; margin-bottom:10px;">
            <strong>📍 ENTREGA:</strong><br>
            ${d.street}, ${d.number}<br>
            ${d.neighborhood} ${d.complement ? "- " + d.complement : ""}<br>
            Taxa Cobrada: R$ ${taxaDossie}
        </div>
        <div style="background:#222; padding:10px; border-radius:5px;">
            <strong>🍔 ITENS ORIGINAIS:</strong><br>
            ${itensLegiveis}
        </div>
        <p style="font-size:0.8rem; color:#666; margin-top:10px; text-align:center;">
            ID Auditoria: ${Date.now()}-${d.id}
        </p>`;
  document.getElementById("modal-dossier").style.display = "flex";
}

function fecharDossie() {
  document.getElementById("modal-dossier").style.display = "none";
}

// FILTROS

function abrirModalFiltro() {
  document.getElementById("modal-filter-orders").style.display = "flex";
}

function fecharModalFiltro() {
  document.getElementById("modal-filter-orders").style.display = "none";
}

function toggleDatasManuais() {
  const val = document.getElementById("filter-period").value;
  const row = document.getElementById("filter-dates-row");
  if (row) row.style.display = val === "manual" ? "flex" : "none";
}

function aplicarFiltros() {
  const period = document.getElementById("filter-period").value;
  const name = document.getElementById("filter-name").value;
  const payment = document.getElementById("filter-payment").value;
  const id = document.getElementById("filter-id").value;

  let start = "";
  let end = "";
  const hoje = new Date();

  if (period === "hoje") {
    start = hoje.toISOString().split("T")[0];
    end = start;
  } else if (period === "mes") {
    const primeiroDia = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    start = primeiroDia.toISOString().split("T")[0];
    end = hoje.toISOString().split("T")[0];
  } else if (period === "ano") {
    const primeiroDia = new Date(hoje.getFullYear(), 0, 1);
    start = primeiroDia.toISOString().split("T")[0];
    end = hoje.toISOString().split("T")[0];
  } else if (period === "manual") {
    start = document.getElementById("filter-start").value;
    end = document.getElementById("filter-end").value;
  }

  const filtros = {};
  if (start) filtros.start_date = start;
  if (end) filtros.end_date = end;
  if (name) filtros.customer_name = name;
  if (payment) filtros.payment_method = payment;
  if (id) filtros.order_id = id;

  carregarPedidosAdmin(filtros);
  fecharModalFiltro();
}

function limparFiltros() {
  document.getElementById("filter-period").value = "hoje";
  document.getElementById("filter-name").value = "";
  document.getElementById("filter-payment").value = "";
  document.getElementById("filter-id").value = "";
  toggleDatasManuais();
  aplicarFiltros();
}

function abrirModalFiltroRelatorio() {
  document.getElementById("modal-filter-reports").style.display = "flex";
}

function fecharModalFiltroRelatorio() {
  document.getElementById("modal-filter-reports").style.display = "none";
}

function toggleDatasRelatorio() {
  const val = document.getElementById("rep-period").value;
  const row = document.getElementById("rep-dates-row");
  if (row) row.style.display = val === "manual" ? "flex" : "none";
}

function aplicarFiltroRelatorio() {
  const period = document.getElementById("rep-period").value;
  const payment = document.getElementById("rep-payment").value;

  let start = "",
    end = "";
  const hoje = new Date();

  // Padrão de segurança: Hoje
  start = hoje.toISOString().split("T")[0];
  end = start;

  try {
    if (period === "hoje") {
      start = hoje.toISOString().split("T")[0];
      end = start;
    } else if (period === "semana") {
      const primeiroDia = new Date(hoje);
      const diaDaSemana = hoje.getDay();
      primeiroDia.setDate(hoje.getDate() - diaDaSemana);
      start = primeiroDia.toISOString().split("T")[0];
      end = hoje.toISOString().split("T")[0];
    } else if (period === "mes") {
      const primeiroDia = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
      start = primeiroDia.toISOString().split("T")[0];
      end = hoje.toISOString().split("T")[0];
    } else if (period === "manual") {
      const s = document.getElementById("rep-start").value;
      const e = document.getElementById("rep-end").value;
      if (s && e) {
        start = s;
        end = e;
      }
    }
  } catch (e) {
    console.warn("Erro data", e);
  }

  const filtros = {};
  if (start) filtros.start_date = start;
  if (end) filtros.end_date = end;
  if (payment) filtros.payment_method = payment;

  carregarDashboard(filtros);
  fecharModalFiltroRelatorio();
}

// Função para alternar abas
function openConfigTab(tabName) {
  // Esconde todos
  document.getElementById("tab-horarios").style.display = "none";
  document.getElementById("tab-avaliacoes").style.display = "none";

  // Remove classe active dos botões
  document
    .querySelectorAll(".config-tabs .tab-btn")
    .forEach((b) => b.classList.remove("active"));

  // Mostra o selecionado
  document.getElementById(tabName).style.display = "block";
  event.currentTarget.classList.add("active");

  // Se for a aba de avaliações, carrega os dados
  if (tabName === "tab-avaliacoes") {
    carregarAvaliacoesAdmin();
  }
}

// 2. Carrega as avaliações com a URL da API correta
/**
 * Carrega as avaliações dos clientes no painel administrativo.
 * Ajustado para utilizar o padrão de cookies HttpOnly do sistema.
 */
async function carregarAvaliacoesAdmin() {
  const tbody = document.getElementById("admin-reviews-tbody");
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="5">Carregando...</td></tr>';

  try {
    // Busca os dados usando o prefixo /api definido no api.js
    // credentials: "include" é essencial para enviar o cookie de sessão
    const res = await fetch("/api/avaliar/listar", {
      method: "GET",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!res.ok) throw new Error("Falha na requisição");

    const data = await res.json();

    tbody.innerHTML = "";
    if (!data || data.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="5">Nenhuma avaliação encontrada.</td></tr>';
      return;
    }

    data.forEach((rev) => {
      const row = `
            <tr>
                <td>${rev.date || "---"}</td>
                <td>${rev.author || "Anônimo"}</td>
                <td style="color: #f1c40f;">${rev.stars} ★</td>
                <td><small>${rev.coment || "(Sem comentário)"}</small></td>
                <td>
                    <button onclick="window.deletarAvaliacaoAdmin(${
                      rev.id
                    })" class="btn-small" 
                        style="background:#e74c3c; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">
                        <i class="fa-solid fa-trash"></i> Excluir
                    </button>
                </td>
            </tr>`;
      tbody.innerHTML += row;
    });
  } catch (error) {
    console.error("Erro ao carregar avaliações:", error);
    tbody.innerHTML =
      '<tr><td colspan="5" style="color:#e74c3c;">Erro ao carregar dados do servidor.</td></tr>';
  }
}

/**
 * Exclui uma avaliação permanentemente.
 * @param {number} id - ID da avaliação
 */
async function deletarAvaliacaoAdmin(id) {
  if (!confirm("ADMIN: Tem certeza que deseja excluir este comentário?"))
    return;

  try {
    const res = await fetch(`/api/avaliar/admin/${id}`, {
      method: "DELETE",
      credentials: "include",
    });

    if (res.ok) {
      showToast("Avaliação excluída com sucesso!", "success");
      carregarAvaliacoesAdmin(); // Atualiza a lista
    } else {
      const data = await res.json();
      showToast(data.error || "Erro ao excluir avaliação.", "error");
    }
  } catch (error) {
    showToast("Erro de conexão com o servidor.", "error");
  }
}

try {
  window.switchPanel = switchPanel;
  window.adminLogout = adminLogout;
  window.carregarCozinha = carregarCozinha;
  window.moverParaPreparo = moverParaPreparo;
  window.moverParaEntrega = moverParaEntrega;
  window.concluirPedidoDefinitivo = concluirPedidoDefinitivo;
  window.carregarPedidosAdmin = carregarPedidosAdmin;
  window.mudarStatus = mudarStatus;
  window.carregarMenuAdmin = carregarMenuAdmin;
  window.toggleProd = toggleProd;
  window.openProductModal = openProductModal;
  window.editarProduto = editarProduto;
  window.closeProductModal = closeProductModal;
  window.addDetailRow = addDetailRow;
  window.removeDetailRow = removeDetailRow;
  window.deletarProduto = deletarProduto;
  window.closeSecurityModal = closeSecurityModal;
  window.executarDelecao = executarDelecao;
  window.carregarListaConversas = carregarListaConversas;
  window.selecionarChat = selecionarChat;
  window.carregarChatAtivo = carregarChatAtivo;
  window.enviarRespostaAdmin = enviarRespostaAdmin;
  window.handleAdminChatKey = handleAdminChatKey;
  window.switchConfigTab = switchConfigTab;
  window.carregarCuponsAdmin = carregarCuponsAdmin;
  window.toggleNewCouponForm = toggleNewCouponForm;
  window.deletarCupom = deletarCupom;
  window.carregarUsuariosAdmin = carregarUsuariosAdmin;
  window.abrirGaleriaNuvem = abrirGaleriaNuvem;
  window.fecharGaleriaNuvem = fecharGaleriaNuvem;
  window.selecionarImagemCloud = selecionarImagemCloud;
  window.apagarImagemCloud = apagarImagemCloud;
  window.carregarBairrosAdmin = carregarBairrosAdmin;
  window.adicionarBairro = adicionarBairro;
  window.apagarBairro = apagarBairro;
  window.imprimirComanda = imprimirComanda;
  window.carregarHorariosAdmin = carregarHorariosAdmin;
  window.salvarHorarios = salvarHorarios;
  window.carregarDashboard = carregarDashboard;
  window.abrirDossie = abrirDossie;
  window.fecharDossie = fecharDossie;
  window.abrirModalFiltro = abrirModalFiltro;
  window.fecharModalFiltro = fecharModalFiltro;
  window.toggleDatasManuais = toggleDatasManuais;
  window.aplicarFiltros = aplicarFiltros;
  window.limparFiltros = limparFiltros;
  window.abrirModalFiltroRelatorio = abrirModalFiltroRelatorio;
  window.fecharModalFiltroRelatorio = fecharModalFiltroRelatorio;
  window.toggleDatasRelatorio = toggleDatasRelatorio;
  window.aplicarFiltroRelatorio = aplicarFiltroRelatorio;
  window.openConfigTab = openConfigTab;
  window.carregarAvaliacoesAdmin = carregarAvaliacoesAdmin;
  window.deletarAvaliacaoAdmin = deletarAvaliacaoAdmin;
} catch (e) {
  console.error("Erro ao expor funções globais do Admin:", e);
}
