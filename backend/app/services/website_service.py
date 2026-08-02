from bson import ObjectId

from app.config.database import website_collection

from app.schemas.website_schema import website_serializer, websites_serializer


def create_website(data):

    result = website_collection.insert_one(data)

    return website_serializer(

        website_collection.find_one({"_id": result.inserted_id})

    )


def get_all_websites():

    return websites_serializer(

        website_collection.find()

    )


def get_website(id):

    return website_serializer(

        website_collection.find_one({"_id": ObjectId(id)})

    )


def delete_website(id):

    website_collection.delete_one(

        {"_id": ObjectId(id)}

    )

    return {"message":"Deleted Successfully"}


def update_website(id,data):

    website_collection.update_one(

        {"_id":ObjectId(id)},

        {"$set":data}

    )

    return website_serializer(

        website_collection.find_one(

            {"_id":ObjectId(id)}

        )

    )