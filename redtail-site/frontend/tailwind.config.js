/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
  	extend: {
  		opacity: Object.fromEntries(Array.from({ length: 101 }, (_, i) => [i, `${i / 100}`])),
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			ink: '#0A0A0B',
  			pulse: '#FF2E2E',
  			platinum: '#E2E2E2',
  			moss: '#B4FF39',
  			ghost: '#8FB3FF',
  			panel: '#15151A',
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			},
  			sidebar: {
  				DEFAULT: 'hsl(var(--sidebar-background))',
  				foreground: 'hsl(var(--sidebar-foreground))',
  				primary: 'hsl(var(--sidebar-primary))',
  				'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
  				accent: 'hsl(var(--sidebar-accent))',
  				'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
  				border: 'hsl(var(--sidebar-border))',
  				ring: 'hsl(var(--sidebar-ring))'
  			}
  		},
  		fontFamily: {
  			heading: ['var(--font-heading)'],
  			body: ['var(--font-body)'],
  			display: ['var(--font-display)'],
  			mono: ['var(--font-mono)'],
  			pixel: ['"Press Start 2P"', 'monospace']
  		},
  		keyframes: {
  			scan: {
  				'0%': { top: '0%' },
  				'100%': { top: '100%' }
  			},
  			blink: {
  				'0%, 49%': { opacity: '1' },
  				'50%, 100%': { opacity: '0' }
  			},
  			bob: {
  				'0%, 100%': { transform: 'translateY(0)' },
  				'50%': { transform: 'translateY(-6px)' }
  			},
  			flicker: {
  				'0%, 100%': { opacity: '1' },
  				'41%': { opacity: '1' },
  				'42%': { opacity: '0.82' },
  				'43%': { opacity: '1' },
  				'45%': { opacity: '0.9' },
  				'46%': { opacity: '1' },
  				'78%': { opacity: '1' },
  				'79%': { opacity: '0.75' },
  				'80%': { opacity: '1' }
  			},
  			buzz: {
  				'0%, 100%': { opacity: '1' },
  				'8%': { opacity: '0.35' },
  				'9%': { opacity: '1' },
  				'11%': { opacity: '0.6' },
  				'12%': { opacity: '1' },
  				'37%': { opacity: '1' },
  				'38%': { opacity: '0.2' },
  				'39%': { opacity: '0.9' },
  				'40%': { opacity: '0.3' },
  				'41%': { opacity: '1' },
  				'70%': { opacity: '1' },
  				'71%': { opacity: '0.5' },
  				'72%': { opacity: '1' }
  			},
  			neon: {
  				'0%, 100%': { opacity: '0.55' },
  				'50%': { opacity: '1' },
  				'62%': { opacity: '0.4' },
  				'64%': { opacity: '0.95' }
  			},
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			scan: 'scan 1.4s linear infinite',
  			blink: 'blink 1s steps(1) infinite',
  			bob: 'bob 2.4s ease-in-out infinite',
  			flicker: 'flicker 6s steps(1) infinite',
  			neon: 'neon 4.5s ease-in-out infinite',
  			buzz: 'buzz 3.2s steps(1) infinite',
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
}
