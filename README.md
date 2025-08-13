# 5G Availability Checker - Modern UI/UX

A comprehensive 5G network availability checker with a modern, responsive web interface. Check 5G availability for any address in Australia using Telstra's network data.

## 🚀 Features

### Modern UI/UX
- **Dark/Light Theme Toggle** - Switch between themes with persistent storage
- **Responsive Design** - Works perfectly on desktop, tablet, and mobile devices
- **Modern Typography** - Uses Inter font family for better readability
- **Smooth Animations** - Hover effects, transitions, and loading animations
- **Interactive Components** - Cards, buttons, and form elements with modern styling

### Three Interface Options

#### 1. **Checker Page** (`/`)
- Simple, focused interface for quick address checks
- Real-time progress indicators
- Export results to CSV
- Live and database check options

#### 2. **Dashboard** (`/dashboard`)
- Comprehensive overview with statistics
- Side-by-side checker and map
- Real-time stats tracking
- Tabbed results and analytics sections
- Quick stats cards

#### 3. **Map View** (`/map`)
- Interactive map visualization
- Coverage pattern analysis
- Custom markers for available/unavailable locations
- Export map data
- Legend and controls

### Enhanced Functionality
- **Real-time Progress Bars** - Visual feedback during checks
- **Statistics Dashboard** - Track total checks, availability rates, and coverage
- **Export Capabilities** - Download results as CSV files
- **Error Handling** - Beautiful error messages with icons
- **Loading States** - Animated spinners and progress indicators
- **Navigation** - Easy switching between different views

## 🎨 Design System

### Color Scheme
- **Light Theme**: Clean whites and grays with blue accents
- **Dark Theme**: Deep blues and grays with lighter accents
- **Success**: Green for available 5G
- **Error**: Red for unavailable 5G
- **Warning**: Orange for alerts

### Typography
- **Primary Font**: Inter (Google Fonts)
- **Weights**: 400, 500, 600, 700, 800
- **Responsive**: Scales appropriately on all devices

### Components
- **Cards**: Elevated containers with shadows and hover effects
- **Buttons**: Gradient primary buttons, outlined secondary buttons
- **Forms**: Modern input fields with focus states
- **Icons**: Font Awesome 6.4.0 for consistent iconography

## 🛠️ Technical Features

### Frontend
- **CSS Custom Properties** - Theme-aware styling
- **CSS Grid & Flexbox** - Modern layout techniques
- **CSS Animations** - Smooth transitions and keyframes
- **JavaScript ES6+** - Modern JavaScript features
- **WebSocket Integration** - Real-time data updates

### Backend Integration
- **FastAPI** - Modern Python web framework
- **WebSocket Support** - Real-time communication
- **Static File Serving** - Optimized asset delivery
- **Template Rendering** - Jinja2 templates

## 📱 Responsive Design

### Breakpoints
- **Desktop**: 1200px+ - Full layout with side-by-side sections
- **Tablet**: 768px-1024px - Stacked layout with adjusted spacing
- **Mobile**: <768px - Single column, optimized touch targets

### Mobile Optimizations
- Touch-friendly button sizes
- Simplified navigation
- Optimized form layouts
- Reduced animations for performance

## 🎯 User Experience

### Accessibility
- **Keyboard Navigation** - Full keyboard support
- **Screen Reader Friendly** - Proper ARIA labels and semantic HTML
- **High Contrast** - Theme-aware contrast ratios
- **Focus Indicators** - Clear focus states for all interactive elements

### Performance
- **Optimized Assets** - Compressed CSS and efficient fonts
- **Lazy Loading** - Map tiles load on demand
- **Smooth Animations** - Hardware-accelerated CSS transitions
- **Efficient JavaScript** - Minimal DOM manipulation

## 🚀 Getting Started

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python app.py
   ```

3. **Access the Interface**
   - **Checker**: http://localhost:8000/
   - **Dashboard**: http://localhost:8000/dashboard
   - **Map**: http://localhost:8000/map

## 📊 Usage

### Basic Check
1. Enter an address in the search field
2. Select search radius and number of addresses
3. Choose between "Check Live" or "Check Database"
4. View real-time results with progress indicators

### Map Visualization
1. Navigate to the Map page
2. Configure bounding box coordinates
3. Select data source (Live or CSV)
4. Start mapping to see coverage patterns

### Dashboard Overview
1. Use the Dashboard for comprehensive analysis
2. Monitor real-time statistics
3. Export data for further analysis
4. Switch between results and analytics tabs

## 🎨 Customization

### Theme Colors
Modify CSS custom properties in `static/style.css`:
```css
:root {
  --accent-primary: #3b82f6;
  --accent-secondary: #1d4ed8;
  --success-color: #10b981;
  --error-color: #ef4444;
}
```

### Adding New Pages
1. Create new template in `templates/`
2. Add route in `app.py`
3. Update navigation in existing templates
4. Add page-specific styles

## 🔧 Development

### File Structure
```
├── app.py                 # FastAPI application
├── static/
│   └── style.css         # Main stylesheet
├── templates/
│   ├── form.html         # Checker page
│   ├── dashboard.html    # Dashboard page
│   └── map.html          # Map page
└── README.md             # This file
```

### Styling Guidelines
- Use CSS custom properties for theme-aware colors
- Follow BEM methodology for class naming
- Implement responsive design with mobile-first approach
- Use semantic HTML elements
- Ensure accessibility compliance

## 🎉 Future Enhancements

- [ ] Advanced analytics with charts and graphs
- [ ] User authentication and saved searches
- [ ] API rate limiting and caching
- [ ] Real-time notifications
- [ ] Advanced filtering and sorting
- [ ] Integration with additional network providers
- [ ] Mobile app development
- [ ] Advanced map features (heatmaps, clustering)

## 📄 License

This project is open source and available under the MIT License.

---

**Built with ❤️ using FastAPI, modern CSS, and JavaScript** 