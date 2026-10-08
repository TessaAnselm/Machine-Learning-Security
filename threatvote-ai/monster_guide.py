"""Render the project's monster as an animated, accessible guide."""

import base64
import html
from pathlib import Path

import streamlit as st


@st.cache_data
def monster_image(animated=False):
    filename = 'monster-talking.gif' if animated else 'monster-talking-still.png'
    return base64.b64encode(Path(__file__).with_name(filename).read_bytes()).decode('ascii')


def show_guide(title, message, *, motion=True, celebrate=False):
    classes = 'monster monster-party' if motion and celebrate else 'monster'
    still = (f'<img class="monster-still" src="data:image/png;base64,{monster_image()}" '
             'alt="Your pink monster guide holding a cookie" />')
    if motion:
        character = (f'<img class="monster-animated" src="data:image/gif;base64,{monster_image(True)}" '
                     'alt="Monster moves its mouth, blinks, and munches a cookie" />' + still)
    else:
        character = still
    st.html(f"""
    <style>
      .monster-guide {{ display:flex; align-items:center; gap:24px; padding:20px;
        border:2px solid #c084fc; border-radius:24px; margin:12px 0 24px;
        background:var(--secondary-background-color, #f5f3ff); }}
      .monster {{ width:180px; max-width:30%; flex-shrink:0;
        transform-origin:bottom center; }}
      .monster img {{ display:block; width:100%; }}
      .monster:has(.monster-animated) .monster-still {{ display:none; }}
      .monster-party {{ animation:monster-party .8s ease-in-out 3; }}
      .monster-guide h3 {{ margin:0 0 8px; }}
      .monster-guide p {{ margin:0; font-size:1.1rem; line-height:1.6; }}
      @keyframes monster-party {{
        0%,100% {{ transform:translateY(0) rotate(0); }}
        25% {{ transform:translateY(-18px) rotate(-8deg); }}
        75% {{ transform:translateY(-18px) rotate(8deg); }}
      }}
      @media (prefers-reduced-motion: reduce) {{
        .monster {{ animation:none; }}
        .monster .monster-animated {{ display:none; }}
        .monster:has(.monster-animated) .monster-still {{ display:block; }}
      }}
      @media (max-width:600px) {{ .monster-guide {{ gap:12px; padding:12px; }} }}
    </style>
    <section class="monster-guide" aria-label="Monster's mission guide">
      <div class="{classes}">{character}</div>
      <div><h3>{html.escape(title)}</h3><p>{html.escape(message)}</p></div>
    </section>
    """)
