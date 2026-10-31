/* SellFlow console — API client (no dependencies).
   Same-origin requests to the FastAPI backend under /api/v1. */

const BASE = "/api/v1";
const TOKEN_KEY = "sf.token";

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

function extractDetail(payload) {
  if (!payload) return "";
  const { detail } = payload;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const where = Array.isArray(item.loc) ? item.loc.filter((p) => p !== "body").join(".") : "";
        return `${where ? where + ": " : ""}${item.msg || "invalid value"}`;
      })
      .join("; ");
  }
  return "";
}

export const api = {
  token: localStorage.getItem(TOKEN_KEY) || null,
  user: null,
  businessId: null,

  setToken(token) {
    this.token = token;
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  },

  clearSession() {
    this.setToken(null);
    this.user = null;
    this.businessId = null;
  },

  async request(method, path, { json, query, form, root } = {}) {
    const url = new URL((root ? "" : BASE) + path, window.location.origin);
    if (query) {
      for (const [key, value] of Object.entries(query)) {
        if (value !== undefined && value !== null && value !== "") {
          url.searchParams.set(key, value);
        }
      }
    }
    const headers = { Accept: "application/json" };
    if (json !== undefined) headers["Content-Type"] = "application/json";
    if (this.token) headers.Authorization = `Bearer ${this.token}`;

    let response;
    try {
      response = await fetch(url.toString(), {
        method,
        headers,
        body: json !== undefined ? JSON.stringify(json) : form,
      });
    } catch (networkError) {
      throw new ApiError(0, "Network unreachable. Check the connection and try again.");
    }

    if (response.status === 401) {
      window.dispatchEvent(new CustomEvent("sf:unauthorized"));
    }
    if (response.status === 204) return null;

    const text = await response.text();
    let payload = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = null;
    }
    if (!response.ok) {
      throw new ApiError(response.status, extractDetail(payload) || response.statusText);
    }
    return payload;
  },

  get(path, query, options) {
    return this.request("GET", path, { query, ...options });
  },
  post(path, json, query, options) {
    return this.request("POST", path, { json, query, ...options });
  },
  put(path, json, query) {
    return this.request("PUT", path, { json, query });
  },
  patch(path, json) {
    return this.request("PATCH", path, { json });
  },
  del(path) {
    return this.request("DELETE", path);
  },

  /* ---------------------------------------------------------------- auth */
  login(email, password) {
    return this.post("/auth/login", { email, password });
  },
  register(payload) {
    return this.post("/auth/register", payload);
  },
  me() {
    return this.get("/auth/me");
  },
  updateMe(payload) {
    return this.put("/auth/me", payload);
  },
  changePasscode(current_password, new_password) {
    return this.post("/auth/passcode/change", { current_password, new_password });
  },

  /* ----------------------------------------------------------- business */
  updateBusiness(id, payload) {
    return this.patch(`/businesses/${id}`, payload);
  },

  /* ---------------------------------------------------------- analytics */
  summary(businessId, params = {}) {
    return this.get(`/businesses/${businessId}/analytics/summary`, params);
  },

  /* ----------------------------------------------------------- products */
  products(businessId) {
    return this.get(`/businesses/${businessId}/products/`);
  },
  createProduct(businessId, payload) {
    return this.post(`/businesses/${businessId}/products/`, payload);
  },
  updateProduct(businessId, productId, payload) {
    return this.put(`/businesses/${businessId}/products/${productId}`, payload);
  },
  deleteProduct(businessId, productId) {
    return this.del(`/businesses/${businessId}/products/${productId}`);
  },
  uploadProduct(businessId, formData) {
    return this.request("POST", `/businesses/${businessId}/products/upload`, { form: formData });
  },

  /* ---------------------------------------------------------- customers */
  customers(businessId) {
    return this.get(`/businesses/${businessId}/customers/`);
  },
  createCustomer(businessId, payload) {
    return this.post(`/businesses/${businessId}/customers/`, payload);
  },
  updateCustomer(businessId, customerId, payload) {
    return this.put(`/businesses/${businessId}/customers/${customerId}`, payload);
  },
  deleteCustomer(businessId, customerId) {
    return this.del(`/businesses/${businessId}/customers/${customerId}`);
  },

  /* ------------------------------------------------------------- orders */
  orders(businessId, params = {}) {
    return this.get(`/businesses/${businessId}/orders/`, params);
  },
  createOrder(businessId, payload) {
    return this.post(`/businesses/${businessId}/orders/`, payload);
  },
  order(businessId, orderId) {
    return this.get(`/businesses/${businessId}/orders/${orderId}`);
  },
  setOrderStatus(businessId, orderId, status) {
    return this.patch(`/businesses/${businessId}/orders/${orderId}/status`, { status });
  },

  /* ---------------------------------------------------------- deliveries */
  delivery(businessId, orderId) {
    return this.get(`/businesses/${businessId}/orders/${orderId}/delivery/`);
  },
  createDelivery(businessId, orderId, payload) {
    return this.post(`/businesses/${businessId}/orders/${orderId}/delivery/`, payload);
  },
  updateDelivery(businessId, orderId, payload) {
    return this.patch(`/businesses/${businessId}/orders/${orderId}/delivery/`, payload);
  },

  /* ----------------------------------------------------------- payments */
  payments(businessId) {
    return this.get(`/businesses/${businessId}/payments`);
  },
  recordPayment(businessId, orderId, payload) {
    return this.post(`/businesses/${businessId}/orders/${orderId}/payments/`, payload);
  },

  /* ------------------------------------------------- payment intelligence */
  intelligenceEvents(businessId, params = {}) {
    return this.get(`/businesses/${businessId}/payments/intelligence/events`, params);
  },
  intelligenceSummary(businessId) {
    return this.get(`/businesses/${businessId}/payments/intelligence/summary`);
  },
  intelligenceFeedback(businessId, payload) {
    return this.post(`/businesses/${businessId}/payments/intelligence/feedback`, payload);
  },

  /* ---------------------------------------------------- payment accounts */
  paymentAccounts(businessId) {
    return this.get("/payment-accounts", { business_id: businessId }, { root: true });
  },
  connectPaymentAccount(businessId, payload) {
    return this.post("/payment-accounts/connect", payload, { business_id: businessId }, { root: true });
  },
};
