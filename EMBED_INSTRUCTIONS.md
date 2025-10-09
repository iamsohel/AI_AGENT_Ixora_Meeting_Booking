# How to Embed iXora AI Assistant on Your Website

## Quick Start

Add this code snippet to your website's HTML, right before the closing `</body>` tag:

```html
<!-- iXora AI Meeting Assistant -->
<div id="ixora-chat-widget"></div>
<script>
  (function() {
    var iframe = document.createElement('iframe');
    iframe.src = 'http://localhost:5173'; // Replace with your production URL
    iframe.style.cssText = 'position:fixed;bottom:0;right:0;width:100%;height:100%;border:none;pointer-events:none;z-index:9999;';
    iframe.id = 'ixora-chat-iframe';
    iframe.allow = 'clipboard-write';
    document.body.appendChild(iframe);

    // Allow pointer events only on the iframe content
    iframe.onload = function() {
      iframe.style.pointerEvents = 'auto';
    };
  })();
</script>
```

## Production Deployment

### 1. Build the Frontend

```bash
cd frontend
npm run build
```

### 2. Deploy the Built Files

The `dist/` folder can be deployed to:
- Netlify
- Vercel
- AWS S3 + CloudFront
- Your own server

### 3. Update the API URL

In your deployment environment, set the API URL:

```bash
# .env.production
VITE_API_URL=https://your-api-domain.com
```

### 4. Embed Code for Production

```html
<!-- iXora AI Meeting Assistant -->
<div id="ixora-chat-widget"></div>
<script src="https://your-chat-widget-url.com/embed.js"></script>
```

## Customization

### Color Scheme

The widget uses your iXora brand colors:
- Primary Red: `#E31E24`
- Dark Background: `#1a1a1a`
- Darker Background: `#0d0d0d`

These can be customized in `frontend/src/App.css` under the `:root` section.

### Welcome Message

Edit the welcome message in `frontend/src/App.jsx`:

```javascript
text: "Hi! I'm your iXora AI assistant 👋\n\nI can help you schedule a meeting..."
```

## Widget Position

The widget appears as a floating chat button in the bottom-right corner by default.

To change position, edit `frontend/src/App.css`:

```css
.app {
  bottom: 20px;  /* Adjust vertical position */
  right: 20px;   /* Adjust horizontal position */
}
```

## Browser Support

- Chrome/Edge: ✓
- Firefox: ✓
- Safari: ✓
- Mobile browsers: ✓

## Security

- CORS is configured for localhost in development
- Update CORS origins in `api.py` for production:

```python
allow_origins=["https://your-website.com"]
```
