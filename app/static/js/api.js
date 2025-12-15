// site/js/api.js

import { showToast } from "./main.js";

// Configuração Dinâmica de Ambiente
const isLocalhost =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

export const API_BASE_URL = "/api";

/**
 * HELPER CENTRALIZADO DE REQUISIÇÕES
 * * Refatorado para HttpOnly:
 * 1. Não lê token do localStorage.
 * 2. Garante credentials: "include" para enviar o cookie.
 * 3. Permite sobrescrever headers se necessário (ex: reset de senha).
 */
async function fetchAuth(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  // Headers padrão
  const defaultHeaders = {
    "Content-Type": "application/json",
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers, // Permite que quem chama adicione headers extras (ex: Authorization manual)
    },
    credentials: "include", // 🔥 OBRIGATÓRIO: Envia o Cookie HttpOnly para o backend
  };

  const response = await fetch(url, config);
  return response;
}

// -----------------------------------------------------------------------------
// FUNÇÕES UTILITÁRIAS
// -----------------------------------------------------------------------------

function adaptarProduto(produtoBack) {
  let detalhes = {};
  if (typeof produtoBack.details_json === "string") {
    try {
      detalhes = JSON.parse(produtoBack.details_json);
    } catch (e) {
      detalhes = {};
    }
  } else if (produtoBack.details) {
    detalhes = produtoBack.details;
  }

  return {
    id: produtoBack.id,
    name: produtoBack.name,
    description: produtoBack.description,
    price: parseFloat(produtoBack.price),
    image: produtoBack.image_url || "assets/burger_classic.png",
    carnes: detalhes.carnes || [],
    adicionais: detalhes.adicionais || [],
    acompanhamentos: detalhes.acompanhamentos || [],
    bebidas: detalhes.bebidas || [],
    details: detalhes,
  };
}

function extrairNomes(lista) {
  if (!lista) return [];
  return lista.map((i) => (typeof i === "string" ? i : i.nome));
}

function enviarWhatsApp(data, id) {
  const tel = "5534996537883";
  const texto =
    `*NOVO PEDIDO #${id}*\n` +
    `----------------------------------\n` +
    `👤 *${data.name}*\n` +
    `📱 ${data.phone}\n` +
    `📍 ${data.address}, ${data.number}\n` +
    (data.bairro ? `🏘️ ${data.bairro}\n` : "") +
    (data.comp ? `📌 ${data.comp}\n` : "") +
    `----------------------------------\n` +
    `🛒 *RESUMO:*\n${data.resumoCarrinho}\n` +
    `----------------------------------\n` +
    `💰 *TOTAL: R$ ${data.total.toFixed(2)}*\n\n` +
    `📝 *Obs:* ${data.message}`;

  const url = `https://api.whatsapp.com/send?phone=${tel}&text=${encodeURIComponent(
    texto
  )}`;
  window.open(url, "_blank");
}

// -----------------------------------------------------------------------------
// ROTAS DE API (Clean Code)
// -----------------------------------------------------------------------------

// --- CARDÁPIO ---
export const fetchMenu = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/menu/lanches`);
    return res.ok ? (await res.json()).map(adaptarProduto) : [];
  } catch (e) {
    return [];
  }
};

export const fetchCombos = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/menu/combos`);
    return res.ok ? (await res.json()).map(adaptarProduto) : [];
  } catch (e) {
    return [];
  }
};

export const fetchBebidas = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/menu/bebidas`);
    return res.ok ? (await res.json()).map(adaptarProduto) : [];
  } catch (e) {
    return [];
  }
};

// --- PEDIDOS ---
export async function submitOrder(frontData, abrirWhatsapp = true) {
  const itemsFormatados = frontData.cartItems.map((item) => ({
    product_id: item.productId || item.id,
    quantity: item.quantity,
    customizations: {
      carnes: extrairNomes(item.details?.carnes),
      adicionais: extrairNomes(item.details?.adicionais),
      acompanhamentos: extrairNomes(item.details?.acompanhamentos),
      bebidas: extrairNomes(item.details?.bebidas),
      obs: item.details?.obs || "",
    },
  }));

  const payload = {
    customer: {
      name: frontData.name,
      phone: frontData.phone,
      address: {
        street: frontData.address,
        number: frontData.number,
        neighborhood: frontData.bairro,
        complement: frontData.comp,
      },
    },
    items: itemsFormatados,
    payment_method: frontData.payment_method,
    coupon_code: frontData.coupon_code,
  };

  try {
    const response = await fetchAuth("/orders/create", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (response.status === 401) {
      showToast("Sua sessão expirou. Faça login novamente.", "warning");
      import("./auth.js").then((module) => module.logout());
      return { success: false, error: "Sessão expirada" };
    }

    const dados = await response.json();
    if (!response.ok) throw new Error(dados.error || "Falha ao salvar pedido");

    if (abrirWhatsapp) enviarWhatsApp(frontData, dados.id);

    return {
      success: true,
      orderId: dados.id,
      redirectUrl: dados.redirect_url,
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// --- AUTENTICAÇÃO (Login/Register não retornam token visível mais) ---
export async function loginUser(email, password) {
  try {
    const response = await fetchAuth("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Erro ao entrar");
    // O backend já setou o cookie. Retornamos apenas o user para a UI.
    return { success: true, user: data.user };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

export async function registerUser(userData) {
  try {
    const response = await fetchAuth("/auth/register", {
      method: "POST",
      body: JSON.stringify(userData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Erro ao cadastrar");
    return { success: true, user: data.user };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

export async function updateUserProfile(userData) {
  try {
    const response = await fetchAuth("/auth/update", {
      method: "PUT",
      body: JSON.stringify(userData),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Erro ao atualizar");
    return { success: true, user: data.user };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

export async function fetchCurrentUser() {
  try {
    // O navegador envia o cookie automaticamente
    const response = await fetchAuth("/auth/me");
    if (response.status === 401 || response.status === 403) return null;
    if (!response.ok) return null;
    return await response.json();
  } catch (error) {
    return null;
  }
}

// --- OUTROS ---
export async function fetchAddresses() {
  try {
    return (await fetchAuth("/address")).json();
  } catch {
    return [];
  }
}
export async function addAddress(addrData) {
  try {
    return (
      await fetchAuth("/address", {
        method: "POST",
        body: JSON.stringify(addrData),
      })
    ).ok;
  } catch {
    return false;
  }
}
export async function setActiveAddress(id) {
  try {
    await fetchAuth(`/address/${id}/active`, { method: "PATCH" });
    return true;
  } catch {
    return false;
  }
}
export async function deleteAddress(id) {
  try {
    await fetchAuth(`/address/${id}`, { method: "DELETE" });
    return true;
  } catch {
    return false;
  }
}
export async function fetchMyOrders() {
  try {
    const res = await fetchAuth("/orders/me");
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function getChatMessages() {
  try {
    const res = await fetchAuth("/chat");
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function sendChatMessage(text) {
  try {
    return (
      await fetchAuth("/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
      })
    ).ok;
  } catch {
    return false;
  }
}
// Admin, Config, Delivery, etc... (O padrão fetchAuth resolve tudo)
export async function fetchAdminMenu() {
  try {
    const res = await fetchAuth("/menu/admin");
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function toggleAvailability(id) {
  try {
    return (await fetchAuth(`/menu/${id}/toggle`, { method: "PATCH" })).ok;
  } catch {
    return false;
  }
}
export async function updateOrderStatus(id, status) {
  try {
    return (
      await fetchAuth(`/orders/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      })
    ).ok;
  } catch {
    return false;
  }
}
export async function fetchAdminConversations() {
  try {
    const res = await fetchAuth("/chat/admin/conversations");
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function fetchAdminUserHistory(userId) {
  try {
    const res = await fetchAuth(`/chat/admin/history/${userId}`);
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function sendAdminReply(userId, text) {
  try {
    return (
      await fetchAuth("/chat/admin/reply", {
        method: "POST",
        body: JSON.stringify({ user_id: userId, message: text }),
      })
    ).ok;
  } catch {
    return false;
  }
}
export async function uploadImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  try {
    // Upload não usa JSON, então chamamos fetch direto
    const res = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });
    if (!res.ok) throw new Error();
    return (await res.json()).url;
  } catch {
    return null;
  }
}
export async function createProduct(data) {
  try {
    return (
      await fetchAuth("/menu", { method: "POST", body: JSON.stringify(data) })
    ).ok;
  } catch {
    return false;
  }
}
export async function updateProduct(id, data) {
  try {
    return (
      await fetchAuth(`/menu/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      })
    ).ok;
  } catch {
    return false;
  }
}
export async function deleteProduct(id, password) {
  try {
    const res = await fetchAuth(`/menu/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ password }),
    });
    return res.ok;
  } catch {
    return { error: "Erro" };
  }
}
export async function fetchCoupons() {
  try {
    const res = await fetchAuth("/config/coupons");
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function createCoupon(data) {
  try {
    return (
      await fetchAuth("/config/coupons", {
        method: "POST",
        body: JSON.stringify(data),
      })
    ).ok;
  } catch {
    return false;
  }
}
export async function deleteCoupon(id) {
  try {
    return (await fetchAuth(`/config/coupons/${id}`, { method: "DELETE" })).ok;
  } catch {
    return false;
  }
}
export async function fetchUsersList() {
  try {
    const res = await fetchAuth("/config/users");
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function fetchPublicCoupons() {
  try {
    const res = await fetch(`${API_BASE_URL}/config/coupons/public`);
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function fetchCloudGallery() {
  try {
    const res = await fetchAuth("/upload/gallery");
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function deleteCloudImage(publicId) {
  try {
    return (
      await fetchAuth("/upload/gallery", {
        method: "DELETE",
        body: JSON.stringify({ public_id: publicId }),
      })
    ).ok;
  } catch {
    return false;
  }
}
export async function fetchNeighborhoodsAdmin() {
  const res = await fetchAuth("/delivery/admin");
  return res.ok ? await res.json() : [];
}
export async function fetchNeighborhoodsPublic() {
  try {
    const res = await fetch(`${API_BASE_URL}/delivery`);
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function addNeighborhood(data) {
  return (
    await fetchAuth("/delivery", { method: "POST", body: JSON.stringify(data) })
  ).ok;
}
export async function deleteNeighborhood(id) {
  return (await fetchAuth(`/delivery/${id}`, { method: "DELETE" })).ok;
}
export async function fetchSchedule() {
  try {
    const res = await fetch(`${API_BASE_URL}/config/schedule`);
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
export async function updateSchedule(data) {
  try {
    return (
      await fetchAuth("/config/schedule", {
        method: "PUT",
        body: JSON.stringify(data),
      })
    ).ok;
  } catch {
    return false;
  }
}
export async function fetchDashboardStats(filtros = {}) {
  try {
    const params = new URLSearchParams(filtros).toString();
    const res = await fetchAuth(`/reports/dashboard?${params}`);
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}
export async function fetchOrderDossier(id) {
  try {
    const res = await fetchAuth(`/reports/dossier/${id}`);
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}
export async function fetchAdminOrders(filtros = {}) {
  try {
    const params = new URLSearchParams(filtros).toString();
    const res = await fetchAuth(`/orders/admin?${params}`);
    return res.ok ? await res.json() : [];
  } catch {
    return [];
  }
}
