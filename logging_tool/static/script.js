document.addEventListener("DOMContentLoaded", function () {
	const titleContainer = document.getElementById("file-title");
    const contentContainer = document.getElementById("file-content");
	const sidebarContainer = document.querySelector(".sidebar");
	const folderStates = JSON.parse(localStorage.getItem("folderStates")) || {};
	
	let currentFilePath = localStorage.getItem("lastViewedFile") || null;  // Store the currently viewed file
	
	const TRIANGLE_DOWN = '\u25BC'
	const TRIANGLE_RIGHT = '\u25B6'
	
	function fetchFileContent(filePath, updateHistory = true) {
		if (!filePath) return;  // Avoid fetching when no file is selected
        fetch(`/get_file_content?path=${encodeURIComponent(filePath)}`)
            .then(response => response.text())
            .then(newContent => {
				titleContainer.innerText = decodeURIComponent(filePath); // Show relative path
				
                if (contentContainer.innerHTML !== newContent) {
                    contentContainer.innerHTML = newContent; // Update only if content changed
                }
				
				if (updateHistory) {
                    history.pushState(null, "", `/view/${filePath}`); // Update URL without reloading
                    localStorage.setItem("lastViewedFile", filePath);  // Save the last opened file
                }
				currentFilePath = filePath; // Update the current file being viewed
            })
            .catch(error => console.error("Error fetching file:", error));
    }
	
	
	function fetchSidebarUpdate() {
        fetch("/get_sidebar")
            .then(response => response.text())
            .then(newSidebar => {
				const tempContainer = document.createElement("div");
				tempContainer.innerHTML = newSidebar;
				
                // Update only changed parts
                updateSidebar(sidebarContainer, tempContainer);
				
				restoreFolderStates(folderStates); // Restore states after update
                attachSidebarListeners(); // Reattach event listeners after update
            })
            .catch(error => console.error("Error fetching sidebar:", error));
    }
	
	
	function updateSidebar(oldSidebar, newSidebar) {
        const oldItems = oldSidebar.querySelectorAll("li");
        const newItems = newSidebar.querySelectorAll("li");

        if (oldItems.length !== newItems.length) {
            oldSidebar.innerHTML = newSidebar.innerHTML;
            return;
        }

        oldItems.forEach((oldItem, index) => {
            const newItem = newItems[index];

            // Replace only if content differs
            if (oldItem.innerHTML !== newItem.innerHTML) {
                oldItem.innerHTML = newItem.innerHTML;
            }
        });
    }


	function restoreFolderStates() {
        document.querySelectorAll(".folder").forEach(folder => {
            const folderName = folder.dataset.path;
            const sublist = folder.querySelector("ul");
            const toggle = folder.querySelector(".toggle #triangle");

            if (folderStates[folderName]) {
                sublist.style.display = "block";
                toggle.textContent = TRIANGLE_DOWN;
            } else {
                sublist.style.display = "none";
                toggle.textContent = TRIANGLE_RIGHT;
            }
        });
    }


    function attachSidebarListeners() {
		document.querySelectorAll(".folder .toggle").forEach(toggle => {
			
			restoreFolderStates()
			
			toggle.addEventListener("click", function () {
				let triangle = toggle.querySelector("#triangle");
                let parent = this.parentElement;
                let sublist = parent.querySelector("ul");
                let folderName = parent.dataset.path;

                const isVisible = sublist.style.display === "block";
                sublist.style.display = isVisible ? "none" : "block";
				triangle.textContent = isVisible ? TRIANGLE_RIGHT : TRIANGLE_DOWN;
                folderStates[folderName] = !isVisible;

                localStorage.setItem("folderStates", JSON.stringify(folderStates));
            });
		});
			
		document.querySelectorAll(".file-link").forEach(link => {
			link.addEventListener("click", function (event) {
				event.preventDefault();
				fetchFileContent(this.dataset.path);
			});
        });
    }
	

    // Search functionality
    const searchInput = document.getElementById("search");
    searchInput.addEventListener("input", function () {
        let filter = this.value.toLowerCase();
        document.querySelectorAll(".sidebar ul li").forEach(item => {
            let text = item.textContent.toLowerCase();
            if (text.includes(filter)) {
                item.style.display = "block";
                // Ensure parent folders remain visible
                let parent = item.parentElement;
                while (parent && parent.classList.contains("folder")) {
                    parent.style.display = "block";
                    parent = parent.parentElement;
                }
            } else {
                item.style.display = "none";
            }
        });
    });
	
	
	attachSidebarListeners()
	
	setInterval(() => fetchFileContent(currentFilePath, false), 3000);	// Refresh content
	setInterval(fetchSidebarUpdate, 5000); // Refresh sidebar
	
	// Load last viewed file on page refresh
    if (currentFilePath) {
        fetchFileContent(currentFilePath, false);
    }
	
});

