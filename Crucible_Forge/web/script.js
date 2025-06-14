document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const goalInput = document.getElementById('goal-input');
    const startButton = document.getElementById('start-button');
    const executeButton = document.getElementById('execute-button');
    const stopButton = document.getElementById('stop-button');
    const logOutput = document.getElementById('log-output');
    const planContainer = document.getElementById('plan-container');
    const fileExplorer = document.getElementById('file-explorer');
    const agentStatus = document.getElementById('agent-status');
    const statusText = document.getElementById('status-text');
    const tabs = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    // --- State ---
    let currentPlan = null;
    let socket = null;

    // --- Functions ---
    const logMessage = (message, type = 'info') => {
        // Sanitize message to prevent HTML injection
        const sanitizedMessage = message.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        logOutput.innerHTML += `\n<span class="log-${type}">${sanitizedMessage}</span>`;
        logOutput.scrollTop = logOutput.scrollHeight; // Auto-scroll
    };

    const setAgentStatus = (status, text) => {
        agentStatus.className = `status-${status}`;
        statusText.textContent = text.toUpperCase();
    };

    const connectWebSocket = () => {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws/log`);

        socket.onopen = () => {
            console.log('WebSocket connection established.');
            logMessage('Connected to agent logs.', 'success');
        };

        socket.onmessage = (event) => {
            try {
                const messageData = JSON.parse(event.data);
                
                if (messageData.type === 'plan_generated') {
                    currentPlan = messageData.plan;
                    displayPlan(currentPlan);
                    setAgentStatus('idle', 'Awaiting Approval');
                    executeButton.disabled = false;
                } else if (messageData.type === 'file_structure') {
                    fileExplorer.textContent = messageData.data;
                }
            } catch (e) {
                // If it's not JSON, it's a plain log message
                logMessage(event.data);
            }
        };

        socket.onclose = () => {
            console.log('WebSocket connection closed. Attempting to reconnect...');
            logMessage('Connection lost. Reconnecting...', 'error');
            setAgentStatus('error', 'Disconnected');
            setTimeout(connectWebSocket, 3000); // Reconnect after 3 seconds
        };

        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            logMessage('WebSocket error.', 'error');
        };
    };

    const displayPlan = (plan) => {
        planContainer.innerHTML = ''; // Clear previous plan
        if (!plan || plan.length === 0) {
            planContainer.innerHTML = '<p>The generated plan is empty or invalid.</p>';
            return;
        }
        plan.forEach((task, index) => {
            const taskEl = document.createElement('div');
            taskEl.className = 'plan-task';
            
            const toolName = task.tool_name || 'unknown_tool';
            const params = task.parameters ? JSON.stringify(task.parameters, null, 2) : '{}';

            taskEl.innerHTML = `
                <div><strong>Task ${index + 1}:</strong> <span class="tool-name">${toolName}</span></div>
                <pre class="params">${params}</pre>
            `;
            planContainer.appendChild(taskEl);
        });
    };

    // --- API Calls ---
    const startAgent = async () => {
        const goal = goalInput.value.trim();
        if (!goal) {
            alert('Please enter a development goal.');
            return;
        }

        logOutput.innerHTML = ''; // Clear logs
        logMessage(`Starting agent with goal: ${goal}`);
        setAgentStatus('running', 'Planning');
        startButton.disabled = true;
        executeButton.disabled = true;

        try {
            const response = await fetch('/api/start-agent', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            logMessage(data.message, 'success');
        } catch (error) {
            console.error('Error starting agent:', error);
            logMessage(`Failed to start agent: ${error.message}`, 'error');
            setAgentStatus('error', 'Error');
            startButton.disabled = false;
        }
    };

    const executePlan = async () => {
        if (!currentPlan) {
            alert('No plan available to execute.');
            return;
        }

        logMessage('Executing approved plan...');
        setAgentStatus('running', 'Executing');
        executeButton.disabled = true;

        try {
            const response = await fetch('/api/execute-plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plan: currentPlan }),
            });
             if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            logMessage(data.message, 'success');
        } catch (error) {
            console.error('Error executing plan:', error);
            logMessage(`Failed to execute plan: ${error.message}`, 'error');
            setAgentStatus('error', 'Error');
        } finally {
             startButton.disabled = false; // Ready for new goal
        }
    };
    
    const stopAgent = async () => {
        logMessage('Stopping agent...', 'warning');
        try {
             await fetch('/api/stop-agent', { method: 'POST' });
             setAgentStatus('idle', 'Stopped');
             startButton.disabled = false;
             executeButton.disabled = true;
        } catch(error) {
            logMessage(`Failed to stop agent: ${error.message}`, 'error');
        }
    };

    // --- Event Listeners ---
    startButton.addEventListener('click', startAgent);
    executeButton.addEventListener('click', executePlan);
    stopButton.addEventListener('click', stopAgent);
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Deactivate all
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            // Activate clicked
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });

    // --- Initialization ---
    connectWebSocket();
});
