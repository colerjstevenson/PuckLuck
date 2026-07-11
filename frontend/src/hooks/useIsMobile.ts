import { useEffect, useState } from "react";

export function useIsMobile(breakpoint = 768): boolean {
  const query = `(max-width: ${breakpoint}px)`;

  const getMatches = () => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.matchMedia(query).matches;
  };

  const [isMobile, setIsMobile] = useState(getMatches);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const mediaQuery = window.matchMedia(query);
    const onChange = () => setIsMobile(mediaQuery.matches);

    onChange();

    mediaQuery.addEventListener("change", onChange);
    return () => {
      mediaQuery.removeEventListener("change", onChange);
    };
  }, [query]);

  return isMobile;
}
