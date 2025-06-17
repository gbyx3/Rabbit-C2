document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  const agentId = urlParams.get("agent_id");
  const agentCard = agentId
    ? document.querySelector(`.agent-card[data-agent-id="${agentId}"]`)
    : null;

  if (agentCard) {
    const addJobButton = agentCard.querySelector(".add-job");
    if (addJobButton) {
      addJobButton.addEventListener("click", async (e) => {
        const card = e.target.closest(".agent-card");
        const input = card.querySelector(".job-input");
        const command = input.value.trim();
        if (!command) {
          alert("Please enter a command");
          return;
        }
        try {
          const response = await fetch("/admin/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent_id: agentId, command }),
          });
          const result = await response.json();
          if (result.status === "success") {
            input.value = "";
              window.location.reload();
          } else {
            alert(`Error: ${result.message}`);
          }
        } catch (error) {
          alert(`Error: ${error.message}`);
        }
      });
    }

    agentCard.querySelectorAll(".delete-x").forEach((button) => {
      button.addEventListener("click", async (e) => {
        const card = e.target.closest(".agent-card");
        const jobItem = e.target.closest(".job-item");
        const sequence = jobItem.dataset.sequence;
        try {
          const response = await fetch("/admin/", {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent_id: agentId, sequence }),
          });
          const result = await response.json();
          if (result.status === "success") {
            window.location.reload();
          } else {
            alert(`Error: ${result.message}`);
          }
        } catch (error) {
          alert(`Error: ${error.message}`);
        }
      });
    });

    agentCard.querySelectorAll(".copy-output").forEach((button) => {
      button.addEventListener("click", async (e) => {
        const jobItem = e.target.closest(".job-item");
        const output = jobItem.querySelector("pre").textContent;
        try {
          await navigator.clipboard.writeText(output);
        } catch (error) {
          alert(`Error copying output: ${error.message}`);
        }
      });
    });
  }

  // Agent Management Functionality
  const addAgentBtn = document.getElementById("add-agent-btn");
  if (addAgentBtn) {
    const addAgentForm = document.getElementById("add-agent-form");
    const addAddAgentBtn = document.getElementById("add-add-agent-btn");
    const cancleAddAgentBtn = document.getElementById("cancle-add-agent-btn");
    addAgentBtn.addEventListener("click", () => {
      addAgentForm.reset();
      addAgentForm.classList.remove("hidden");
    });
    cancleAddAgentBtn.addEventListener("click", () => {
      addAgentForm.classList.add("hidden");
    });
    addAddAgentBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      const formData = new FormData(addAgentForm);
      const data = Object.fromEntries(formData);
      try {
        const response = await fetch("/agent/manage/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const result = await response.json();
        if (result.result === "success") {
          console.log("Agent added successfully: ", result.message);
          addAgentForm.classList.add("hidden");
          window.location.reload();
        }
      } catch (error) {
        alert(`Error: ${error.message}`);
      }
    });
  }
  const deleteAgentBtn = document.getElementById("delete-agent-btn");
  if (deleteAgentBtn) {
    deleteAgentBtn.addEventListener("click", async (e) => {
      const agentId = e.target.dataset.agentId;
      if (confirm(`Are you sure you want to delete agent ${agentId}?`)) {
        try {
          const response = await fetch(`/agent/manage/?agent_id=${agentId}`, {
            method: "DELETE",
          });
          const result = await response.json();
          if (result.result === "success") {
            window.location.href = "/admin/";
          }
        } catch (error) {
          alert(`Error: ${error.message}`);
        }
      }
    });
  }
});
