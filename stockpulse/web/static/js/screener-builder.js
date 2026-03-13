function screenerBuilder() {
    return {
        conditions: [{ field: '', operator: '', value: '' }],
        name: '',
        description: '',
        category: 'custom',
        previewHtml: '',
        previewCount: 0,
        addCondition() { this.conditions.push({ field: '', operator: '', value: '' }); },
        removeCondition(idx) { this.conditions.splice(idx, 1); },
        parseConditions() {
            return this.conditions
                .filter(c => c.field && c.operator)
                .map(c => {
                    let val = c.value;
                    if (['is_true', 'is_false'].includes(c.operator)) val = null;
                    else if (!isNaN(val) && val !== '') val = parseFloat(val);
                    return { field: c.field, operator: c.operator, value: val };
                });
        },
        async preview() {
            const resp = await fetch(window.location.href, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'preview', conditions: this.parseConditions() }),
            });
            this.previewHtml = await resp.text();
            const rows = (this.previewHtml.match(/<tr>/g) || []).length - 1;
            this.previewCount = Math.max(0, rows);
        },
        async save() {
            if (!this.name) { alert('Name is required'); return; }
            const resp = await fetch(window.location.href, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'save',
                    name: this.name,
                    description: this.description,
                    category: this.category,
                    conditions: this.parseConditions(),
                }),
            });
            const data = await resp.json();
            if (data.id) { window.location.href = '/screeners/' + data.id; }
            else { alert(data.error || 'Failed to save'); }
        },
    };
}
