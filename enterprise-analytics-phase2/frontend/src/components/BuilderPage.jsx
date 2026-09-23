/*
import { useState } from "react";
import { Rnd } from "react-rnd";
import MiniChart from "./MiniChart";

export default function BuilderPage({
  analyticsItems,
  setAnalyticsItems,
}) {
  const [selected, setSelected] = useState([]);

  return (
    <div
      style={{
        width: "100%",
        height: "100vh",
        position: "relative",
        background: "#0f172a",
        overflow: "auto",
      }}
    >
      <h2
        style={{
          color: "#fff",
          padding: 20,
          margin: 0,
        }}
      >
        Dashboard Builder
      </h2>

      {analyticsItems.map((item, index) => (
        <Rnd
          key={item.id || index}
          size={{
            width: item.width || 500,
            height: item.height || 350,
          }}
          position={{
            x: item.x || 50,
            y: item.y || 50,
          }}
          bounds="parent"
          onDragStop={(e, d) => {
            const updated = [...analyticsItems];

            updated[index] = {
              ...updated[index],
              x: d.x,
              y: d.y,
            };

            setAnalyticsItems(updated);
          }}
          onResizeStop={(e, direction, ref, delta, position) => {
            const updated = [...analyticsItems];

            updated[index] = {
              ...updated[index],
              width: parseInt(ref.style.width, 10),
              height: parseInt(ref.style.height, 10),
              x: position.x,
              y: position.y,
            };

            setAnalyticsItems(updated);
          }}
        >
          <div
            style={{
              background: "#0a1220",
              border: "1px solid #1e3a5f",
              borderRadius: 12,
              padding: 12,
              height: "100%",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                color: "#94a3b8",
                fontSize: 12,
                fontWeight: 600,
                marginBottom: 12,
                flexShrink: 0,
              }}
            >
              {item.title}
            </div>

            <div
              style={{
                flex: 1,
                minHeight: 0,
                height: "100%",
              }}
            >
              <MiniChart chart={item.chart} />
            </div>
          </div>
        </Rnd>
      ))}

      {analyticsItems.length === 0 && (
        <div
          style={{
            color: "#64748b",
            textAlign: "center",
            marginTop: 100,
            fontSize: 14,
          }}
        >
          No charts added yet.
          <br />
          Go to Saved Insights and click "Add To Builder".
        </div>
      )}
    </div>
  );
}
  */
 import { useState } from "react";
import { Rnd } from "react-rnd";
import MiniChart from "./MiniChart";

export default function BuilderPage({
  analyticsItems,
  setAnalyticsItems,
}) {
  const [selected, setSelected] = useState([]);

  return (
    <div
      style={{
        width: "100%",
        height: "100vh",
        position: "relative",
        background: "#0f172a",
        overflow: "auto",
      }}
    >
      <h2
        style={{
          color: "#fff",
          padding: 20,
          margin: 0,
        }}
      >
        Dashboard Builder
      </h2>

      {analyticsItems.map((item, index) => (
        <Rnd
          key={item.id || index}
          size={{
            width: item.width || 500,
            height: item.height || 350,
          }}
          position={{
            x: item.x || 50,
            y: item.y || 50,
          }}
          bounds="parent"
          onDragStop={(e, d) => {
            const updated = [...analyticsItems];
            updated[index] = {
              ...updated[index],
              x: d.x,
              y: d.y,
            };
            setAnalyticsItems(updated);
          }}
          onResizeStop={(e, direction, ref, delta, position) => {
            const updated = [...analyticsItems];
            updated[index] = {
              ...updated[index],
              width: parseInt(ref.style.width, 10),
              height: parseInt(ref.style.height, 10),
              x: position.x,
              y: position.y,
            };
            setAnalyticsItems(updated);
          }}
        >
          {/* Changed box-sizing and explicit sizing to help inner charts recalculate safely */}
          <div
            style={{
              background: "#0a1220",
              border: "1px solid #1e3a5f",
              borderRadius: 12,
              padding: 12,
              width: "100%",
              height: "100%",
              boxSizing: "border-box", 
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                color: "#94a3b8",
                fontSize: 12,
                fontWeight: 600,
                marginBottom: 12,
                flexShrink: 0,
              }}
            >
              {item.title}
            </div>

            {/* Container for the actual chart */}
            <div
              style={{
                flexGrow: 1,
                width: "100%",
                height: "100%",
                minHeight: 0,
                position: "relative" // Helps relative-positioned charts calculate 100% correctly
              }}
            >
              <MiniChart chart={item.chart} />
            </div>
          </div>
        </Rnd>
      ))}

      {analyticsItems.length === 0 && (
        <div
          style={{
            color: "#64748b",
            textAlign: "center",
            marginTop: 100,
            fontSize: 14,
          }}
        >
          No charts added yet.
          <br />
          Go to Saved Insights and click "Add To Builder".
        </div>
      )}
    </div>
  );
}
