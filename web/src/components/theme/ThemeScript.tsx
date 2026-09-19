import { THEME_STORAGE_KEY } from "@/lib/theme";

/** Applies the stored contrast theme before paint to avoid a flash. */
export function ThemeScript() {
  const code = `(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});if(t==="light"||t==="high"||t==="dark"){document.documentElement.dataset.theme=t;}else{document.documentElement.dataset.theme="dark";}}catch(e){document.documentElement.dataset.theme="dark";}})();`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
