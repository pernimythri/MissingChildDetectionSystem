document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("uploadForm");
    const progressContainer = document.querySelector(".progress-container");
    const progressBar = document.getElementById("progressBar");
    const status = document.getElementById("status");

    // Create redirect button dynamically
    const redirectBtn = document.createElement("button");
    redirectBtn.innerText = "Go to Missing Page";
    redirectBtn.type = "button";
    redirectBtn.style.display = "none";
    redirectBtn.style.marginTop = "10px";
    redirectBtn.style.padding = "10px";
    redirectBtn.style.background = "teal";
    redirectBtn.style.color = "white";
    redirectBtn.style.border = "none";
    redirectBtn.style.cursor = "pointer";

    status.after(redirectBtn);

    form.addEventListener("submit", function (e) {
        e.preventDefault();

        const xhr = new XMLHttpRequest();
        const formData = new FormData(form);

        progressContainer.style.display = "block";
        progressBar.style.width = "0%";
        progressBar.innerText = "0%";
        status.innerText = "";
        redirectBtn.style.display = "none";

        xhr.upload.onprogress = function (event) {
            if (event.lengthComputable) {
                const percent = Math.round((event.loaded / event.total) * 100);
                progressBar.style.width = percent + "%";
                progressBar.innerText = percent + "%";
            }
        };

        xhr.onload = function () {
            if (xhr.status === 200 || xhr.status === 302) {
                progressBar.style.width = "100%";
                progressBar.innerText = "100%";
                status.innerText = "Successfully Uploaded ✅";
                status.style.color = "lightgreen";

                // Show redirect button ONLY after upload completes
                redirectBtn.style.display = "inline-block";
            } else {
                status.innerText = "Upload Failed ❌";
                status.style.color = "red";
            }
        };

        xhr.onerror = function () {
            status.innerText = "Network Error ❌";
            status.style.color = "red";
        };

        xhr.open("POST", window.location.href, true);
        xhr.send(formData);
    });

    // Redirect ONLY when button is clicked
    redirectBtn.addEventListener("click", function () {
        window.location.href = "./templates/missing";
    });

});
