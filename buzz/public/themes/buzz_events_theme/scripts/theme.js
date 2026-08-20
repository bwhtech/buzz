(function () {
	const root = document.documentElement;
	const button = document.getElementById("themeToggle");
	if (!button) return;

	button.addEventListener("click", () => {
		const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
		if (next === "dark") root.setAttribute("data-theme", "dark");
		else root.removeAttribute("data-theme");
		try {
			localStorage.setItem("bp-theme", next);
		} catch (error) {}
	});
})();
