function needsClamp(el) {
  return el.scrollHeight > el.clientHeight + 2;
}

document.querySelectorAll(".card").forEach(card => {
  const p = card.querySelector(".review");
  const btn = card.querySelector(".readmore");
  if (!p || !btn) return;

  // show button only if clamped
  requestAnimationFrame(() => {
    if (needsClamp(p)) btn.classList.remove("hidden");
  });

  let expanded = false;
  btn.addEventListener("click", () => {
    expanded = !expanded;
    if (expanded) {
      p.classList.remove("line-clamp-4");
      btn.textContent = "Show less";
    } else {
      p.classList.add("line-clamp-4");
      btn.textContent = "Read more";
    }
  });
});

