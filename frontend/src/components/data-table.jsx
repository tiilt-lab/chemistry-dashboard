// Simple bordered data table used by settings and people-management dialogs.
// Cells may be strings or React nodes (e.g. action buttons).
function DataTable({ columns, rows }) {
    return (
        <div className="max-h-[60vh] overflow-auto rounded-lg border border-tiilt-line">
            <table className="w-full border-collapse text-left text-sm">
                <thead>
                    <tr>
                        {columns.map((c) => (
                            <th
                                key={c}
                                className="sticky top-0 bg-tiilt-soft px-3 py-2 font-semibold whitespace-nowrap text-tiilt-ink"
                            >
                                {c}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows.length === 0 ? (
                        <tr>
                            <td
                                colSpan={columns.length}
                                className="px-3 py-6 text-center text-tiilt-muted"
                            >
                                Nothing to show.
                            </td>
                        </tr>
                    ) : (
                        rows.map((row, i) => (
                            <tr key={i} className="border-t border-tiilt-line">
                                {row.map((cell, j) => (
                                    <td
                                        key={j}
                                        className="px-3 py-2 whitespace-nowrap text-tiilt-ink"
                                    >
                                        {cell}
                                    </td>
                                ))}
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
        </div>
    )
}

export { DataTable }
