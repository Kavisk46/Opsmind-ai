interface AccessibleDataTableProps {
  caption: string;
  columns: string[];
  rows: (string | number)[][];
}

// Visually hidden equivalent of the SVG chart above it, so screen reader
// users get the same data instead of a silent graphic.
export function AccessibleDataTable({
  caption,
  columns,
  rows,
}: AccessibleDataTableProps) {
  return (
    <table className="sr-only">
      <caption>{caption}</caption>
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column} scope="col">
              {column}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={rowIndex}>
            {row.map((cell, cellIndex) => (
              <td key={cellIndex}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
