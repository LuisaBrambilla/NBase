const themeToggle = document.getElementById("themeToggle");

// Modo escuro desativado: mantem sempre em tema claro.
document.body.classList.add("light");
localStorage.setItem("theme", "light");

if (themeToggle) {
  themeToggle.style.display = "none";
}
