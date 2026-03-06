// This file will handle buttons later
function convertBlocksToPython() {
    var code = Blockly.Python.workspaceToCode(workspace);
    document.getElementById('pythonCode').value = code;
}
