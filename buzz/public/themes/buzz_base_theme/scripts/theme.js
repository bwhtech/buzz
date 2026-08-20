(function () {
	function apply(theme) {
		if (theme === "dark") document.documentElement.setAttribute("data-theme", "dark");
		else document.documentElement.removeAttribute("data-theme");
	}
	function current() {
		return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
	}
	function toggle() {
		var next = current() === "dark" ? "light" : "dark";
		apply(next);
		try {
			localStorage.setItem("bp-theme", next);
		} catch (error) {}
	}
	document.addEventListener("DOMContentLoaded", function () {
		var button = document.getElementById("themeToggle");
		if (button) button.addEventListener("click", toggle);
	});
})();
