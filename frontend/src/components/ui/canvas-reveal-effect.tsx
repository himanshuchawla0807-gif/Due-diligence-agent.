"use client";
import { cn } from "@/lib/utils";
import React, { useEffect, useRef } from "react";

export const CanvasRevealEffect = ({
  animationSpeed = 0.4,
  opacities = [0.3, 0.3, 0.3, 0.5, 0.5, 0.5, 0.8, 0.8, 0.8, 1],
  colors = [[0, 255, 255]],
  containerClassName,
  dotSize,
  showGradient = true,
}: {
  animationSpeed?: number;
  opacities?: number[];
  colors?: number[][];
  containerClassName?: string;
  dotSize?: number;
  showGradient?: boolean;
}) => {
  return (
    <div className={cn("h-full relative bg-white w-full", containerClassName)}>
      <div className="h-full w-full">
        <DotMatrix
          colors={colors ?? [[0, 255, 255]]}
          dotSize={dotSize ?? 3}
          opacities={
            opacities ?? [0.3, 0.3, 0.3, 0.5, 0.5, 0.5, 0.8, 0.8, 0.8, 1]
          }
          center={["x", "y"]}
          animationSpeed={animationSpeed}
        />
      </div>
      {showGradient && (
        <div className="absolute inset-0 bg-gradient-to-t from-gray-950 to-[84%]" />
      )}
    </div>
  );
};

interface DotMatrixProps {
  colors?: number[][];
  opacities?: number[];
  totalSize?: number;
  dotSize?: number;
  center?: ("x" | "y")[];
  animationSpeed?: number;
}

const DotMatrix: React.FC<DotMatrixProps> = ({
  colors = [[0, 0, 0]],
  opacities = [0.04, 0.04, 0.04, 0.04, 0.04, 0.08, 0.08, 0.08, 0.08, 0.14],
  totalSize = 4,
  dotSize = 2,
  animationSpeed = 0.4,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;

    const resizeCanvas = () => {
      const parent = canvas.parentElement;
      if (parent) {
        canvas.width = parent.clientWidth;
        canvas.height = parent.clientHeight;
      }
    };

    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    const render = () => {
      time += 0.01 * animationSpeed;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const width = canvas.width;
      const height = canvas.height;

      // Create a grid of dots
      const cols = Math.ceil(width / totalSize);
      const rows = Math.ceil(height / totalSize);

      for (let i = 0; i < cols; i++) {
        for (let j = 0; j < rows; j++) {
          const x = i * totalSize;
          const y = j * totalSize;

          // Calculate opacity based on noise/randomness similar to the shader
          // Simple pseudo-random based on position and time
          const noise = Math.sin(x * 0.05 + time) * Math.cos(y * 0.05 + time) * 0.5 + 0.5;
          const opacityIndex = Math.floor(noise * opacities.length);
          const opacity = opacities[Math.min(opacityIndex, opacities.length - 1)];

          // Color selection
          const colorIndex = Math.floor(Math.random() * colors.length);
          const color = colors[colorIndex];

          ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${opacity})`;

          // Draw dot
          const drawX = x + (totalSize - dotSize) / 2;
          const drawY = y + (totalSize - dotSize) / 2;

          ctx.beginPath();
          ctx.rect(drawX, drawY, dotSize, dotSize);
          ctx.fill();
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, [colors, opacities, totalSize, dotSize, animationSpeed]);

  return <canvas ref={canvasRef} className="h-full w-full block" />;
};
