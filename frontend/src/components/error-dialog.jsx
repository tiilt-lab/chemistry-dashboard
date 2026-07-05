import { DialogBox } from "../dialog/dialog-component"

// The standard per-page error dialog (alertMessage / showAlert / closeAlert
// pattern) — one definition instead of a hand-copied DialogBox per page.
function ErrorDialog({ message, show, onClose }) {
    return (
        <DialogBox
            itsclass={"add-dialog"}
            heading={"Error"}
            message={message}
            show={show}
            closedialog={onClose}
        />
    )
}

export { ErrorDialog }
