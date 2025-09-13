from flask import Flask, request, jsonify, render_template
from rapidfuzz import process   # for fuzzy search

# 1️⃣ Create Flask app first
app = Flask(__name__)

# 2️⃣ Your dataset (for now, a dictionary)
diseases = {
    "Asthma": {"ICD11": "CA23", "TM2": "TM2-404"},
    "Diabetes mellitus": {"ICD11": "5A11", "TM2": "TM2-101"},
    "Fever": {"ICD11": "MG21", "TM2": "TM2-210"}
}

# 3️⃣ Routes come AFTER app is created
@app.route('/')
def home():
    return render_template("index.html")

# 🔎 Search with fuzzy (FHIR-ready response)
@app.route('/get_code')
def get_code():
    disease = request.args.get("disease", "").strip()
    if not disease:
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{"severity": "error", "code": "invalid", "details": {"text": "No disease provided"}}]
        }), 400

    if disease in diseases:
        codes = diseases[disease]
        fhir_condition = {
            "resourceType": "Condition",
            "id": f"cond-{disease.lower()}",
            "code": {
                "coding": [
                    {
                        "system": "http://id.who.int/icd/release/11",
                        "code": codes["ICD11"],
                        "display": disease
                    },
                    {
                        "system": "http://example.org/tm2",
                        "code": codes["TM2"],
                        "display": f"{disease} (TM2)"
                    }
                ]
            },
            "subject": {"reference": "Patient/P12345"}
        }
        return jsonify(fhir_condition)

    # fuzzy match
    match, score, _ = process.extractOne(disease, diseases.keys())
    if score > 70:
        codes = diseases[match]
        fhir_condition = {
            "resourceType": "Condition",
            "id": f"cond-{match.lower()}",
            "note": f"Did you mean '{match}'?",
            "code": {
                "coding": [
                    {
                        "system": "http://id.who.int/icd/release/11",
                        "code": codes["ICD11"],
                        "display": match
                    },
                    {
                        "system": "http://example.org/tm2",
                        "code": codes["TM2"],
                        "display": f"{match} (TM2)"
                    }
                ]
            },
            "subject": {"reference": "Patient/P12345"}
        }
        return jsonify(fhir_condition)

    return jsonify({
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "error", "code": "not-found", "details": {"text": "Disease not found"}}]
    }), 404


# 📃 List all diseases in FHIR Bundle format
@app.route('/list_diseases')
def list_diseases():
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": []
    }

    for disease, codes in diseases.items():
        condition = {
            "resource": {
                "resourceType": "Condition",
                "id": f"cond-{disease.lower()}",
                "code": {
                    "coding": [
                        {
                            "system": "http://id.who.int/icd/release/11",
                            "code": codes["ICD11"],
                            "display": disease
                        },
                        {
                            "system": "http://example.org/tm2",
                            "code": codes["TM2"],
                            "display": f"{disease} (TM2)"
                        }
                    ]
                },
                "subject": {"reference": "Patient/P12345"}
            }
        }
        bundle["entry"].append(condition)

    return jsonify(bundle)


# ✏️ Update (FHIR OperationOutcome)
@app.route('/update/<disease>', methods=['PUT'])
def update_disease(disease):
    data = request.json
    if disease in diseases:
        diseases[disease]["ICD11"] = data.get("ICD11", diseases[disease]["ICD11"])
        diseases[disease]["TM2"] = data.get("TM2", diseases[disease]["TM2"])
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "information",
                "code": "updated",
                "details": {"text": f"{disease} updated successfully"}
            }]
        })
    return jsonify({
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "error", "code": "not-found", "details": {"text": "Disease not found"}}]
    }), 404


# 🗑️ Delete (FHIR OperationOutcome)
@app.route('/delete/<disease>', methods=['DELETE'])
def delete_disease(disease):
    if disease in diseases:
        del diseases[disease]
        return jsonify({
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "information",
                "code": "deleted",
                "details": {"text": f"{disease} deleted successfully"}
            }]
        })
    return jsonify({
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "error", "code": "not-found", "details": {"text": "Disease not found"}}]
    }), 404


# ⚠️ Error handler (FHIR-style)
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "resourceType": "OperationOutcome",
        "issue": [{"severity": "error", "code": "not-found", "details": {"text": "Resource not found"}}]
    }), 404


# 4️⃣ Run app
if __name__ == "__main__":
    app.run(debug=True)
