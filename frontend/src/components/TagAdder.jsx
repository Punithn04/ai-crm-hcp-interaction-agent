import { useEffect, useRef, useState } from "react";

/** Reusable "search/add + chip list" control used for attendees, materials, and samples. */
export default function TagAdder({ label, items, onAdd, onRemove, searchFn, buttonLabel, placeholder }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef(null);

  useEffect(() => {
    if (!searchFn || !open) return;
    const handle = setTimeout(() => {
      searchFn(query).then(setResults).catch(() => setResults([]));
    }, 200);
    return () => clearTimeout(handle);
  }, [query, open, searchFn]);

  useEffect(() => {
    const onClickOutside = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const handleManualAdd = () => {
    if (query.trim()) {
      onAdd(query.trim());
      setQuery("");
      setOpen(false);
    }
  };

  return (
    <div className="field" ref={boxRef} style={{ position: "relative" }}>
      <label>{label}</label>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          type="text"
          placeholder={placeholder}
          value={query}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onKeyDown={(e) => e.key === "Enter" && handleManualAdd()}
        />
        <button type="button" className="btn" onClick={handleManualAdd}>
          {buttonLabel}
        </button>
      </div>
      {open && results.length > 0 && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            background: "#fff",
            border: "1px solid #d1d5db",
            borderRadius: 6,
            marginTop: 4,
            zIndex: 10,
            maxHeight: 160,
            overflowY: "auto",
          }}
        >
          {results.map((item) => (
            <div
              key={item.id ?? item.name}
              style={{ padding: "8px 10px", cursor: "pointer" }}
              onMouseDown={() => {
                onAdd(item.name);
                setQuery("");
                setOpen(false);
              }}
            >
              {item.name}
            </div>
          ))}
        </div>
      )}
      {items.length === 0 ? (
        <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>No {label.toLowerCase()} added</div>
      ) : (
        <div className="chip-list">
          {items.map((item) => (
            <span className="chip" key={item}>
              {item}
              <button type="button" onClick={() => onRemove(item)}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
