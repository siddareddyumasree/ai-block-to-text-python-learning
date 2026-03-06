let pyodideReadyPromise = null;

// Load Pyodide properly
async function loadPyodideAndPackages() {
    pyodideReadyPromise = await loadPyodide({
        indexURL: "/static/pyodide/"
    });
    console.log("Pyodide loaded successfully!");
}

// Start loading Pyodide immediately
let pyodideLoading = loadPyodideAndPackages();

// Updated runPythonCode to correctly capture printed output
async function runPythonCode() {
    const outputElement = document.getElementById("output");
    outputElement.innerHTML = "Running...";

    try {
        await pyodideLoading;  // Wait until Pyodide fully loads
        const pythonCode = document.getElementById("python-code").value;
        const pyodide = await pyodideReadyPromise;

        // Set up capturing of printed output
        await pyodide.runPythonAsync(`
import sys
from io import StringIO
sys.stdout = StringIO()
`);

        // Run user code
        await pyodide.runPythonAsync(pythonCode);

        // Get printed output
        const printed_output = await pyodide.runPythonAsync('sys.stdout.getvalue()');

        // Show output nicely
        outputElement.innerHTML = `<pre>${printed_output}</pre>`;

        // Reset stdout back to normal
        await pyodide.runPythonAsync('sys.stdout = sys.__stdout__');

    } catch (error) {
        outputElement.innerHTML = `<pre style="color:red;">${error}</pre>`;
    }
}
