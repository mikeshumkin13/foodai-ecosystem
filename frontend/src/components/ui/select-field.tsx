import type { SelectHTMLAttributes } from "react";

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: Array<{ value: string; label: string }>;
};

export function SelectField({ id, label, options, ...props }: SelectFieldProps) {
  const selectId = id ?? props.name;

  return (
    <label className="field" htmlFor={selectId}>
      <span className="field__label">{label}</span>
      <select className="field__input" id={selectId} {...props}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
