const adminToken = localStorage.getItem("admin_token");

if (!adminToken) {
  window.location.href = "./admin_login.html";
}

const logoutTop = document.getElementById("adminLogoutTop");
if (logoutTop) {
  logoutTop.addEventListener("click", () => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_client");
    window.location.href = "./admin_login.html";
  });
}
