def evaluate_model(model, features, target):
    """Return model predictions for downstream metric evaluation."""
    predictions = model.predict(features)
    return {'predictions': predictions, 'target': target}
