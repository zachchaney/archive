document.addEventListener("DOMContentLoaded", function () {
	const titleContainer = document.querySelector(".file-title");
    const fileContentContainer = document.querySelector(".file-content");
	const sidebarContainer = document.querySelector(".sidebar");
	const sidebarContentContainer = document.querySelector(".sidebar-content");
	const searchInput = document.getElementById("search"); // Sidebar search input
	const folderStates = JSON.parse(localStorage.getItem("folderStates")) || {};
	let isUserInteracting = false; // Flag to prevent auto-refresh conflicts
	let currentFilePath = localStorage.getItem("lastViewedFile") || null;  // Store the currently viewed file
	
	const TRIANGLE_DOWN = '\u25BC'
	const TRIANGLE_RIGHT = '\u25B6'
	
	function fetchFileContent(filePath, updateHistory = true, fromUserClick = false) {
		if (!filePath) return;  // Avoid fetching when no file is selected
		
		if (fromUserClick) {
            isUserInteracting = true; // Stop auto-refresh interference
            setTimeout(() => (isUserInteracting = false), 1500); // Resume auto-refresh after delay
        }
		
        fetch(`/get_file_content?path=${encodeURIComponent(filePath)}`)
            .then(response => response.text())
            .then(newContent => {
				if (!fromUserClick && currentFilePath !== filePath) return; // Prevent outdated responses
				titleContainer.innerText = decodeURIComponent(filePath); // Show relative path
				
                if (fileContentContainer.innerHTML !== newContent) {
                    fileContentContainer.innerHTML = newContent; // Update only if content changed
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
		const searchQuery = searchInput.value.toLowerCase(); // Get current search term
		
        fetch("/get_sidebar")
            .then(response => response.text())
            .then(newSidebar => {
				const tempContainer = document.createElement("div");
				tempContainer.innerHTML = newSidebar;
				
                // Update only changed parts
                updateSidebar(sidebarContentContainer, tempContainer);
				
				restoreFolderStates(folderStates); // Restore states after update
                attachSidebarListeners(); // Reattach event listeners after update
				
				applySearchFilter(searchQuery); // Reapply search after updating sidebar
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
	
	
	function applySearchFilter(query) {
        document.querySelectorAll(".sidebar-content li").forEach(item => {
			let text = item.textContent.toLowerCase();
            if (text.includes(query)) {
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
				fetchFileContent(this.dataset.path, true, true);
			});
        });
    }
	

    // Search functionality
    searchInput.addEventListener("input", function () {
        let filter = this.value.toLowerCase();
        document.querySelectorAll(".sidebar-content ul li").forEach(item => {
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
	
	
	// Resizable Sidebar
	let isResizing = false;
	const resizeHandle = document.querySelector(".resize-handle");

	resizeHandle.addEventListener("mousedown", (event) => {
		isResizing = true;
		resizeHandle.classList.add("active");
		document.addEventListener("mousemove", resizeSidebar);
		document.addEventListener("mouseup", stopResize);
	});

	function resizeSidebar(event) {
		if (!isResizing) return;
		let newWidth = event.clientX; // Get mouse X position
		if (newWidth < 150) newWidth = 150; // Min width
		if (newWidth > 1000) newWidth = 1000; // Max width
		sidebarContainer.style.width = `${newWidth}px`;
	}

	function stopResize() {
		isResizing = false;
		resizeHandle.classList.remove("active");
		document.removeEventListener("mousemove", resizeSidebar);
		document.removeEventListener("mouseup", stopResize);
	}
	
	
	// Main
	attachSidebarListeners()
	
	setInterval(fetchSidebarUpdate, 5000); // Refresh sidebar
	
	setInterval(() => {
        if (!isUserInteracting) fetchFileContent(currentFilePath, false);
    }, 3000);
	
	// Load last viewed file on page refresh
    if (currentFilePath) {
        fetchFileContent(currentFilePath, false);
    }
	
});



