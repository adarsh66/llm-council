import { useEffect, useState } from 'react';
import { api } from '../api';
import './Settings.css';

export default function Settings({ isOpen, onClose, mode = 'council' }) {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    setError(null);
    api.getSettings()
      .then((data) => {
        const byMode = (data && data.modes && data.modes[mode]) ? data.modes[mode] : null;
        setSettings(byMode || {
          council_models: (data && data.council_models) || [],
          chairman_model: (data && data.chairman_model) || '',
          title_model: (data && data.title_model) || '',
        });
      })
      .catch((e) => setError(e.message || 'Failed to load settings'))
      .finally(() => setLoading(false));
  }, [isOpen, mode]);

  if (!isOpen) return null;

  const handleChangeModelField = (index, field, value) => {
    setSettings((prev) => {
      const next = { ...prev };
      const models = [...(next.council_models || [])];
      models[index] = { ...models[index], [field]: value };
      next.council_models = models;
      return next;
    });
  };

  const handleAddModel = () => {
    setSettings((prev) => ({
      ...prev,
      council_models: [...(prev.council_models || []), { name: '', system_prompt: '' }],
    }));
  };

  const handleRemoveModel = (index) => {
    setSettings((prev) => {
      const models = [...(prev.council_models || [])];
      models.splice(index, 1);
      return { ...prev, council_models: models };
    });
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setError(null);
      const payload = {
        mode,
        council_models: (settings.council_models || []).map((m) => ({
          name: m.name,
          system_prompt: m.system_prompt || undefined,
        })),
        chairman_model: settings.chairman_model,
        title_model: settings.title_model || undefined,
      };
      await api.updateSettings(payload);
      onClose && onClose();
    } catch (e) {
      setError(e.message || 'Failed to save settings');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-backdrop" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Runtime Settings</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {loading && <div className="settings-loading">Loading…</div>}
        {error && <div className="settings-error">{error}</div>}
        {settings && (
          <div className="settings-content">
            <div className="field-row">
              <label>Chairman Model</label>
              <select
                value={settings.chairman_model || ''}
                onChange={(e) => setSettings((s) => ({ ...s, chairman_model: e.target.value }))}
              {
                ...(!settings.council_models?.length ? { disabled: true } : {})
              }
              >
                {(settings.council_models || []).map((m, idx) => (
                  <option key={idx} value={m.name}>{m.name || '(unnamed)'}</option>
                ))}
              </select>
            </div>

            <div className="field-row">
              <label>Title Model (optional)</label>
              <input
                type="text"
                value={settings.title_model || ''}
                placeholder="e.g., gpt-5-mini"
                onChange={(e) => setSettings((s) => ({ ...s, title_model: e.target.value }))}
              />
            </div>

            <div className="models-section">
              <div className="models-header">
                <h3>Council Models</h3>
                <button className="secondary-btn" onClick={handleAddModel}>Add Model</button>
              </div>
              <div className="models-list">
                {(settings.council_models || []).map((m, index) => (
                  <div key={index} className="model-row">
                    <div className="model-fields">
                      <div className="field">
                        <label>Name</label>
                        <input
                          type="text"
                          value={m.name || ''}
                          onChange={(e) => handleChangeModelField(index, 'name', e.target.value)}
                          placeholder="Azure model name (e.g., gpt-5, phi-4)"
                        />
                      </div>
                      <div className="field">
                        <label>System Prompt (optional)</label>
                        <textarea
                          rows={3}
                          value={m.system_prompt || ''}
                          onChange={(e) => handleChangeModelField(index, 'system_prompt', e.target.value)}
                          placeholder="Custom instructions for this model"
                        />
                      </div>
                    </div>
                    <div className="model-actions">
                      <button className="danger-btn" onClick={() => handleRemoveModel(index)}>Remove</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="settings-actions">
              <button className="secondary-btn" onClick={onClose}>Cancel</button>
              <button className="primary-btn" onClick={handleSave} disabled={loading}>Save</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
