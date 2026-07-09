import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { api } from "../api/client";
import { setHcp } from "../features/interactionForm/formSlice";

export default function HcpSearchInput() {
  const dispatch = useDispatch();
  const hcpName = useSelector((s) => s.form.hcpName);
  const [query, setQuery] = useState(hcpName);
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef(null);

  useEffect(() => setQuery(hcpName), [hcpName]);

  useEffect(() => {
    if (!open) return;
    const handle = setTimeout(() => {
      api.searchHcps(query).then(setResults).catch(() => setResults([]));
    }, 200);
    return () => clearTimeout(handle);
  }, [query, open]);

  useEffect(() => {
    const onClickOutside = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div className="field" ref={boxRef} style={{ position: "relative" }}>
      <label>HCP Name</label>
      <input
        type="text"
        placeholder="Search or select HCP..."
        value={query}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
      />
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
            maxHeight: 200,
            overflowY: "auto",
          }}
        >
          {results.map((hcp) => (
            <div
              key={hcp.id}
              style={{ padding: "8px 10px", cursor: "pointer" }}
              onMouseDown={() => {
                dispatch(setHcp({ id: hcp.id, name: hcp.name }));
                setOpen(false);
              }}
            >
              <div style={{ fontWeight: 500 }}>{hcp.name}</div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>
                {hcp.specialty} {hcp.institution ? `· ${hcp.institution}` : ""}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
