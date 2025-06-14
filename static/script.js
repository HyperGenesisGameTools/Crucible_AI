document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const goalInput = document.getElementById('goal-input');
    const generatePlanButton = document.getElementById('generate-plan-button');
    const executeStepButton = document.getElementById('execute-step-button');
    const stopButton = document.getElementById('stop-button');
    const logOutput = document.getElementById('log-output');
    const planContainer = document.getElementById('plan-container');
    const fileExplorer = document.getElementById('file-explorer');
    const observationOutput = document.getElementById('observation-output');
    const agentStatus = document.getElementById('agent-status');
    const statusText = document.getElementById('status-text');
    const tabs = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    const evaluationToggle = document.getElementById('evaluation-toggle');

    // --- State & Configuration ---
    const API_BASE_URL = 'http://localhost:8000';
    const WS_URL = 'ws://localhost:8000/ws/log';
    let socket = null;
    let isEvaluationEnabled = true;

    // --- Functions ---
    const logMessage = (message, type = 'info') => {
        const sanitizedMessage = message.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        logOutput.innerHTML += `\n<span class="log-${type}">${sanitizedMessage}</span>`;
        logOutput.scrollTop = logOutput.scrollHeight;
    };

    const setAgentStatus = (status, text) => {
        agentStatus.className = `status-${status}`;
        statusText.textContent = text.toUpperCase();
    };

    const updateUIWithState = (state) => {
        console.log("Updating UI with new state:", state);
        
        // Update Plan
        displayPlan(state.master_plan || []);
        
        // Update Observation
        const history = state.observation_history || [];
        const lastObservation = history.length > 0 ? history[history.length - 1] : 'System is ready.';
        observationOutput.textContent = lastObservation;
        observationOutput.scrollTop = 0; // Scroll to top

        // Update Buttons
        const hasPlan = state.master_plan && state.master_plan.length > 0;
        executeStepButton.disabled = !hasPlan || state.is_running;
        generatePlanButton.disabled = state.is_running;
        stopButton.disabled = !state.is_running;

        // Update Status
        if (state.is_running) {
            setAgentStatus('running', 'Executing');
        } else if (hasPlan) {
            setAgentStatus('idle', 'Awaiting Approval');
        } else {
            setAgentStatus('idle', 'Idle');
        }
    };

    const displayPlan = (plan) => {
        planContainer.innerHTML = '';
        if (!plan || plan.length === 0) {
            planContainer.innerHTML = '<p>No steps remaining in the plan.</p>';
            return;
        }
        plan.forEach((task, index) => {
            const taskEl = document.createElement('div');
            taskEl.className = 'plan-task';
            if (index === 0) {
                taskEl.classList.add('next-step'); // Highlight the next step
            }
            
            const toolCall = task.tool_call || {};
            const toolName = toolCall.tool_name || 'unknown_tool';
            const params = toolCall.parameters ? JSON.stringify(toolCall.parameters, null, 2) : '{}';

            taskEl.innerHTML = `
                <button class="rethink-button" data-task-index="${index}" title="Rethink this step">&#x21bb;</button>
                <div class="task-header"><strong>${index === 0 ? 'NEXT STEP' : `Step ${index + 1}`}</strong>: <span class="task-description">${task.description}</span></div>
                <div class="tool-call">
                    <span class="tool-name">${toolName}</span>
                    <pre class="params">${params}</pre>
                </div>
            `;
            planContainer.appendChild(taskEl);
        });
    };

    const connectWebSocket = () => {
        socket = new WebSocket(WS_URL);

        socket.onopen = () => logMessage('🔗 Connected to agent logs.', 'success');
        socket.onclose = () => {
            logMessage('🔌 Connection lost. Attempting to reconnect...', 'error');
            setAgentStatus('error', 'Disconnected');
            setTimeout(connectWebSocket, 3000);
        };
        socket.onerror = () => logMessage('❗️ WebSocket error.', 'error');

        socket.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            switch (msg.type) {
                case 'log':
                    logMessage(msg.data);
                    break;
                case 'file_structure':
                    fileExplorer.textContent = msg.data;
                    break;
                case 'initial_state':
                case 'status_update':
                case 'plan_generated':
                case 'plan_updated':
                case 'observation':
                case 'error':
                    updateUIWithState(msg.state);
                    if (msg.type === 'error') {
                        setAgentStatus('error', 'Error');
                    }
                    if (msg.data) logMessage(msg.data);
                    break;
                default:
                    console.warn("Received unknown message type:", msg.type);
            }
        };
    };

    // --- API Call Handlers ---
    const handleGeneratePlan = async () => {
        const goal = goalInput.value.trim();
        if (!goal) {
            alert('Please enter a development goal.');
            return;
        }
        logOutput.innerHTML = '';
        logMessage(`Submitting goal: ${goal}`);
        setAgentStatus('running', 'Planning');
        generatePlanButton.disabled = true;

        try {
            await fetch(`${API_BASE_URL}/api/generate-plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal }),
            });
        } catch (error) {
            logMessage(`Failed to submit goal: ${error.message}`, 'error');
            setAgentStatus('error', 'Error');
            generatePlanButton.disabled = false;
        }
    };

    const handleExecuteNextStep = async () => {
        logMessage('Approving next step for execution...');
        setAgentStatus('running', 'Executing');
        executeStepButton.disabled = true;

        try {
            await fetch(`${API_BASE_URL}/api/execute-next-step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enable_evaluation: isEvaluationEnabled })
            });
        } catch (error) {
            logMessage(`Failed to execute step: ${error.message}`, 'error');
            setAgentStatus('error', 'Error');
            executeStepButton.disabled = false;
        }
    };
    
    const handleRethinkStep = async (taskIndex) => {
        logMessage(`Requesting rethink for step ${taskIndex + 1}...`, 'warning');
        setAgentStatus('running', 'Rethinking');
        
        try {
            await fetch(`${API_BASE_URL}/api/rethink-step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_index: taskIndex }),
            });
        } catch (error) {
            logMessage(`Failed to rethink step: ${error.message}`, 'error');
            setAgentStatus('error', 'Error');
        }
    };

    const handleStopAgent = async () => {
        logMessage('Requesting agent stop...', 'warning');
        try {
            await fetch(`${API_BASE_URL}/api/stop-agent`, { method: 'POST' });
        } catch (error) {
            logMessage(`Failed to stop agent: ${error.message}`, 'error');
        }
    };

    // --- Event Listeners ---
    generatePlanButton.addEventListener('click', handleGeneratePlan);
    executeStepButton.addEventListener('click', handleExecuteNextStep);
    stopButton.addEventListener('click', handleStopAgent);
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });

    planContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('rethink-button')) {
            const taskIndex = parseInt(e.target.dataset.taskIndex, 10);
            handleRethinkStep(taskIndex);
        }
    });

    evaluationToggle.addEventListener('change', (e) => {
        isEvaluationEnabled = e.target.checked;
        logMessage(`Re-evaluation step is now ${isEvaluationEnabled ? 'ENABLED' : 'DISABLED'}.`, 'info');
    });

    // --- Initialization ---
    connectWebSocket();
});
