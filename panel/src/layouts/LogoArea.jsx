import logoSvg from "../assets/images/Loyan.svg";

export default function LogoArea({ collapsed }) {
  if (collapsed) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: 64,
          padding: "12px 0",
          borderBottom: "3px solid #000",
        }}
      >
        <img
          src={logoSvg}
          alt="LoyanUI"
          style={{ width: 32, height: 32 }}
        />
      </div>
    );
  }

  return (
    <div className="nb-logo">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <img
          src={logoSvg}
          alt="LoyanUI"
          style={{
            width: "clamp(36px, 4vw, 48px)",
            height: "clamp(36px, 4vw, 48px)",
            flexShrink: 0,
          }}
        />
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              fontSize: "clamp(14px, 1.8vw, 17px)",
              fontWeight: 700,
              color: "#000",
            }}
          >
            LoyanUI
          </div>
          <div
            style={{
              fontSize: "clamp(11px, 1.2vw, 13px)",
              color: "#000",
              fontWeight: 600,
            }}
          >
            v1.0.0 Beta
          </div>
        </div>
      </div>
    </div>
  );
}
