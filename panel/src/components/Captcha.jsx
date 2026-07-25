import { useEffect, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import axios from "axios";

const COLORS = ["#8ecac8", "#a8d8d6", "#7ab8b6", "#6dadaa", "#94d0ce"];
const LINE_COUNT = 4;
const DOT_COUNT = 30;

function drawCaptcha(canvas, code) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  ctx.fillStyle = COLORS[Math.floor(Math.random() * COLORS.length)];
  ctx.fillRect(0, 0, w, h);

  for (let i = 0; i < LINE_COUNT; i++) {
    ctx.strokeStyle = `rgba(0,0,0,${0.1 + Math.random() * 0.2})`;
    ctx.lineWidth = 1 + Math.random() * 2;
    ctx.beginPath();
    ctx.moveTo(Math.random() * w, Math.random() * h);
    ctx.lineTo(Math.random() * w, Math.random() * h);
    ctx.stroke();
  }

  for (let i = 0; i < DOT_COUNT; i++) {
    ctx.fillStyle = `rgba(0,0,0,${0.1 + Math.random() * 0.3})`;
    ctx.beginPath();
    ctx.arc(Math.random() * w, Math.random() * h, 1, 0, Math.PI * 2);
    ctx.fill();
  }

  const chars = code.split("");
  const fontSize = h * 0.6;
  ctx.font = `bold ${fontSize}px monospace`;
  ctx.textBaseline = "middle";

  const totalWidth = chars.length * fontSize * 0.8;
  const startX = (w - totalWidth) / 2 + fontSize * 0.4;

  chars.forEach((ch, i) => {
    ctx.fillStyle = `rgba(0,0,0,${0.6 + Math.random() * 0.4})`;
    ctx.save();
    const x = startX + i * fontSize * 0.8;
    const y = h / 2 + (Math.random() - 0.5) * h * 0.15;
    ctx.translate(x, y);
    ctx.rotate(((Math.random() - 0.5) * Math.PI) / 9);
    ctx.fillText(ch, 0, 0);
    ctx.restore();
  });
}

export default function Captcha({ onVerify, style }) {
  const canvasRef = useRef(null);
  const onVerifyRef = useRef(onVerify);
  const { t } = useTranslation();

  onVerifyRef.current = onVerify;

  const fetchCaptcha = useCallback(async () => {
    try {
      const res = await axios.get("/api/loyanui/auth/captcha");
      if (res.data.success) {
        const { id, code } = res.data.data;
        if (canvasRef.current) {
          drawCaptcha(canvasRef.current, code);
        }
        onVerifyRef.current?.(id);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchCaptcha();
  }, [fetchCaptcha]);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, ...style }}>
      <canvas
        ref={canvasRef}
        width={120}
        height={40}
        onClick={fetchCaptcha}
        style={{
          cursor: "pointer",
          borderRadius: 4,
          border: "1px solid #d9d9d9",
        }}
        title={t("captcha.refresh")}
      />
      <span
        onClick={fetchCaptcha}
        style={{ cursor: "pointer", color: "#8ecac8", fontSize: 13 }}
      >
        {t("captcha.refresh")}
      </span>
    </div>
  );
}
