// site/js/ui.js
/**
 * Exibe notificações visuais (toasts) no sistema.
 * Centralizado para ser usado por Clientes e Admins.
 */
export function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  let icon = "fa-circle-info";
  if (type === "success") icon = "fa-circle-check";
  if (type === "error") icon = "fa-circle-xmark";
  if (type === "warning") icon = "fa-triangle-exclamation";

  toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => toast.remove(), 4300);
}

// Mantém compatibilidade global
window.showToast = showToast;
