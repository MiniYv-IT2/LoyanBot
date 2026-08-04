import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "antd";
import "../styles/notfound.css";

function useRandomStars(count, minSize, maxSize) {
  return useMemo(
    () =>
      Array.from({ length: count }, () => ({
        top: Math.random() * 100,
        left: Math.random() * 100,
        size: minSize + Math.random() * (maxSize - minSize),
        delay: Math.random() * 5,
      })),
    [count, minSize, maxSize]
  );
}

export default function NotFound() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const bigStars = useRandomStars(30, 3, 9);
  const smallStars = useRandomStars(30, 1, 4);

  return (
    <>
      <div className="container container-star">
        {bigStars.map((s, i) => (
          <span
            key={`b${i}`}
            className="star-1"
            style={{
              top: `${s.top}%`,
              left: `${s.left}%`,
              "--s": `${s.size}px`,
              animationDelay: `${s.delay}s`,
            }}
          />
        ))}
        {smallStars.map((s, i) => (
          <span
            key={`s${i}`}
            className="star-2"
            style={{
              top: `${s.top}%`,
              left: `${s.left}%`,
              width: `${s.size}px`,
              height: `${s.size}px`,
              animationDelay: `${s.delay}s`,
            }}
          />
        ))}
      </div>
      <div className="container container-bird">
        {Array.from({ length: 6 }).map((_, n) => (
          <div key={n} className="bird bird-anim">
            <div className="bird-container">
              <div className="wing wing-left">
                <div className="wing-left-top" />
              </div>
              <div className="wing wing-right">
                <div className="wing-right-top" />
              </div>
            </div>
          </div>
        ))}
        <div className="container-title">
          <div className="title">
            <span className="number">4</span>
            <div className="moon">
              <div className="face">
                <div className="mouth" />
                <div className="eyes">
                  <div className="eye-left" />
                  <div className="eye-right" />
                </div>
              </div>
            </div>
            <span className="number">4</span>
          </div>
          <div className="subtitle">{t("app.notFound.subtitle")}</div>
          <Button className="nf-back-btn" onClick={() => navigate("/")}>
            {t("app.notFound.back")}
          </Button>
        </div>
      </div>
    </>
  );
}
