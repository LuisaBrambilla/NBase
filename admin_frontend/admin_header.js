const STORAGE_AVATAR_KEY = "admin_avatar";
const profileMenuToggle = document.getElementById("profileMenuToggle");
const profileMenu = document.getElementById("profileMenu");

function applyAvatarToAll() {
  const dataUrl = localStorage.getItem(STORAGE_AVATAR_KEY);
  document.querySelectorAll(".login-avatar").forEach((el) => {
    if (dataUrl) {
      el.style.backgroundImage = "url(" + dataUrl + ")";
      el.classList.add("has-photo");
    } else {
      el.style.backgroundImage = "";
      el.classList.remove("has-photo");
    }
  });
}

applyAvatarToAll();

if (profileMenuToggle && profileMenu) {
  const closeMenu = () => {
    profileMenu.hidden = true;
    profileMenuToggle.setAttribute("aria-expanded", "false");
  };
  const openMenu = () => {
    profileMenu.hidden = false;
    profileMenuToggle.setAttribute("aria-expanded", "true");
  };
  profileMenuToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    profileMenu.hidden ? openMenu() : closeMenu();
  });
  document.addEventListener("click", (e) => {
    if (!profileMenu.contains(e.target) && !profileMenuToggle.contains(e.target)) closeMenu();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMenu();
  });
}
