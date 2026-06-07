const header = document.querySelector("[data-header]");
const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.querySelectorAll(".site-nav a");
const year = document.querySelector("[data-year]");
const contactForm = document.querySelector("[data-contact-form]");
const formNote = document.querySelector("[data-form-note]");

if (year) {
  year.textContent = new Date().getFullYear();
}

if (header && navToggle) {
  navToggle.addEventListener("click", () => {
    const isOpen = header.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });
}

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    if (!header || !navToggle) {
      return;
    }

    header.classList.remove("is-open");
    navToggle.setAttribute("aria-expanded", "false");
  });
});

if (contactForm && formNote) {
  contactForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const formData = new FormData(contactForm);
    const name = String(formData.get("name") || "").trim();
    const email = String(formData.get("email") || "").trim();
    const project = String(formData.get("project") || "").trim();
    const message = String(formData.get("message") || "").trim();

    const body = [
      `Name: ${name}`,
      `Email: ${email}`,
      `Project type: ${project}`,
      "",
      "Message:",
      message || "I would like to discuss a new project.",
    ].join("\n");

    const subject = encodeURIComponent(`New project inquiry from ${name || "a website visitor"}`);
    const encodedBody = encodeURIComponent(body);

    window.location.href = `mailto:hello@struxetechnologies.com?subject=${subject}&body=${encodedBody}`;
    formNote.textContent = "Opening your email app with the project details.";
  });
}
