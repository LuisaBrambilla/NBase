(function () {
  const STORAGE_AVATAR_KEY = "admin_avatar";
  const input = document.getElementById("profileAvatarInput");
  const preview = document.getElementById("profileAvatarPreview");

  if (!input || !preview) return;

  function applySavedPhoto() {
    const dataUrl = localStorage.getItem(STORAGE_AVATAR_KEY);
    if (dataUrl) {
      preview.style.backgroundImage = "url(" + dataUrl + ")";
      preview.classList.add("has-photo");
    } else {
      preview.style.backgroundImage = "";
      preview.classList.remove("has-photo");
    }
  }

  applySavedPhoto();

  input.addEventListener("change", function () {
    const file = input.files && input.files[0];
    if (!file || !file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = function () {
      const dataUrl = reader.result;
      try {
        localStorage.setItem(STORAGE_AVATAR_KEY, dataUrl);
        preview.style.backgroundImage = "url(" + dataUrl + ")";
        preview.classList.add("has-photo");
        if (typeof applyAvatarToAll === "function") applyAvatarToAll();
      } catch (e) {
        if (e.name === "QuotaExceededError") {
          alert("A imagem é grande demais. Escolha uma foto menor.");
        }
      }
    };
    reader.readAsDataURL(file);
    input.value = "";
  });
})();
