import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'
import { CustomEase } from 'gsap/CustomEase'
import '@fontsource-variable/inter'
import '@fontsource/jetbrains-mono'
import './index.css'
import App from './App.jsx'

gsap.registerPlugin(useGSAP, CustomEase)

// The Vivid+Co motion contract's curve (--ease-vivid in tokens.css), as a
// named GSAP ease so timelines can use `ease: "vivid"` instead of
// duplicating the bezier. CustomEase paths use the same 0-1 control-point
// square as CSS cubic-bezier(), so the two stay numerically identical.
CustomEase.create("vivid", "M0,0 C0.52,0.01 0,1 1,1")

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
