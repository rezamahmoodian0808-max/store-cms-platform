// Global Storefront Utilities

window.showToast = function(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg shadow-lg text-white font-medium text-sm transition-opacity duration-300 ${
        type === 'success' ? 'bg-emerald-600' : 'bg-rose-600'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
};

// Simple reactive cart helper using localStorage
window.cartStore = {
    getItems() {
        return JSON.parse(localStorage.getItem('cart_items') || '[]');
    },
    addItem(product) {
        const items = this.getItems();
        items.push({
            ...product,
            added_at: new Date().toISOString()
        });
        localStorage.setItem('cart_items', JSON.stringify(items));
        window.dispatchEvent(new CustomEvent('cart-updated', { detail: items }));
        window.showToast('محصول به سبد خرید افزوده شد / Added to cart');
    },
    count() {
        return this.getItems().length;
    }
};
