export default function FormField({ label, name, value, onChange }) {
  return (
    <label>
      <span>{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(name, event.target.value)}
      />
    </label>
  )
}
